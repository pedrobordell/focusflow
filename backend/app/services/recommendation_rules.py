from schemas.recommendation_schema import HabitContext, Recommendation
from services.recommendation_strategy import RecommendationStrategy

# Umbrales de las reglas. Están arriba y con nombre para que se puedan ajustar (o defender)
# sin buscarlos por el código: son las "perillas" de la estrategia.

# Sesiones mínimas en la ventana de análisis para que un hábito pueda ser el prioritario.
# Con una sola sesión el cumplimiento solo puede valer 0% o 100%, y recomendar a partir de
# ahí sería ruido. Los hábitos con muy poca actividad no se quedan sin atender: de ellos ya
# se encarga la regla de hábitos olvidados.
MIN_WINDOW_SESSIONS = 3

# Días sin cumplir una sesión a partir de los cuales se considera que el hábito está olvidado.
FORGOTTEN_DAYS = 14

# Sesiones consecutivas cumplidas a partir de las cuales se felicita al usuario.
STREAK_MIN = 3

# Tipos de mensaje (dominio de Message.type).
TYPE_RECOMMENDATION = "recommendation"      # el sistema PROPONE un cambio de conducta
TYPE_NOTIFICATION = "notification"          # el sistema INFORMA de un hecho


# 0.75 -> "75%"
def _percent(rate: float) -> str:
    return f"{round(rate * 100)}%"


# Estrategia inicial: REGLAS sobre las métricas del histórico (sin entrenar ningún modelo).
#
# Es una clase, y no un puñado de funciones sueltas, porque implementa RecommendationStrategy:
# el día que se añada una estrategia basada en scikit-learn bastará con crear otra clase que
# herede del mismo interfaz e inyectarla en el servicio.
#
# Ninguno de sus métodos toca la base de datos: solo lee los HabitContext que recibe.
class RulesRecommendationStrategy(RecommendationStrategy):

    def generate(self, contexts: list[HabitContext]) -> list[Recommendation]:
        recommendations = []

        # Orden de relevancia: primero la propuesta (lo que el usuario debería hacer),
        # después los avisos. El dashboard muestra el primer elemento de tipo 'recommendation'.
        priority = self._priority_recommendation(contexts)
        if priority is not None:
            recommendations.append(priority)

        recommendations.extend(self._forgotten_notifications(contexts))
        recommendations.extend(self._streak_notifications(contexts))
        return recommendations

    # --- Regla 1: hábito prioritario + propuesta de franja horaria (RF14) ----

    # Puntuación de prioridad: importancia x (1 - tasa de cumplimiento).
    # Un hábito muy importante que se incumple mucho puntúa alto; uno que ya se cumple
    # siempre puntúa 0 por mucha importancia que tenga. Es la regla del diseño original.
    @staticmethod
    def _priority_score(context: HabitContext) -> float:
        return context.importance * (1 - context.compliance_rate)

    # Elige el hábito sobre el que merece la pena actuar y le propone una franja horaria.
    # Devuelve None si ningún hábito tiene histórico suficiente en la ventana analizada:
    # sin datos el sistema prefiere callarse a inventarse un consejo.
    def _priority_recommendation(self, contexts: list[HabitContext]):
        candidates = [
            context for context in contexts if context.scheduled >= MIN_WINDOW_SESSIONS
        ]
        if not candidates:
            return None

        # Desempates: primero la mayor puntuación, luego la mayor importancia y por último
        # el id más bajo (-habit_id), para que el resultado sea siempre el mismo con los
        # mismos datos. Un mensaje que cambiara en cada recarga no sería defendible.
        target = max(
            candidates,
            key=lambda context: (self._priority_score(context), context.importance, -context.habit_id),
        )

        name = target.habit_name
        # A tope de cumplimiento el mensaje no puede pedir "más foco": cambia el tono.
        if target.compliance_rate >= 1.0:
            title = f"Keep the pace with {name}"
        else:
            title = f"Focus on {name}"

        content = (
            f"You complete {name} {_percent(target.compliance_rate)} of the time "
            f"over the last {target.analysis_days} days."
        )
        if target.best_slot is not None:
            content += (
                f" Your best time slot is {target.best_slot.label} "
                f"({_percent(target.best_slot.probability)} estimated chance of completing it). "
                f"Try scheduling your next session there."
            )
        else:
            # Sin muestra suficiente NO se propone franja: es preferible reconocer que no
            # hay datos a sugerir un horario a partir de una o dos sesiones sueltas.
            content += (
                " There are not enough sessions yet to suggest a time slot: "
                "schedule a few more and the estimate will appear here."
            )

        return Recommendation(type=TYPE_RECOMMENDATION, title=title, content=content)

    # --- Regla 2: hábitos olvidados (RF15) ----------------------------------

    # Un aviso por cada hábito abandonado, del más olvidado al menos.
    def _forgotten_notifications(self, contexts: list[HabitContext]) -> list[Recommendation]:
        found = []      # pares (días de referencia, Recommendation) para poder ordenarlos

        for context in contexts:
            name = context.habit_name

            # Caso A: el hábito existe pero nunca se ha programado ninguna sesión.
            if not context.ever_scheduled:
                found.append((None, Recommendation(
                    type=TYPE_NOTIFICATION,
                    title=f"You have not scheduled {name} yet",
                    content=(
                        f"{name} has no sessions yet, so there is nothing to track. "
                        f"Plan your first one from the calendar."
                    ),
                )))
                continue

            # Días de referencia: desde la última sesión CUMPLIDA o, si nunca ha cumplido
            # ninguna, desde la última que le tocaba. Sin sesiones pasadas no hay olvido
            # posible (un hábito programado para la semana que viene no está abandonado).
            if context.days_since_last_completed is not None:
                days = context.days_since_last_completed
                never_completed = False
            else:
                days = context.days_since_last_session
                never_completed = True
            if days is None or days < FORGOTTEN_DAYS:
                continue

            # Caso B: nunca ha cumplido ninguna de las sesiones que se programó.
            if never_completed:
                content = (
                    f"You have never completed a {name} session, and the last one you "
                    f"scheduled was {days} days ago."
                )
            # Caso C: lo cumplía, pero lleva mucho sin hacerlo.
            else:
                content = f"You haven't completed any {name} session in {days} days."

            found.append((days, Recommendation(
                type=TYPE_NOTIFICATION,
                title=f"You're forgetting {name}",
                content=content,
            )))

        # Primero los que llevan más tiempo olvidados; los "sin programar" (days=None) al final.
        found.sort(key=lambda item: (item[0] is not None, item[0] or 0), reverse=True)
        return [recommendation for _, recommendation in found]

    # --- Regla 3: refuerzo positivo por racha -------------------------------

    # Felicita por las rachas en curso, de la más larga a la más corta.
    def _streak_notifications(self, contexts: list[HabitContext]) -> list[Recommendation]:
        on_streak = [context for context in contexts if context.current_streak >= STREAK_MIN]
        on_streak.sort(key=lambda context: context.current_streak, reverse=True)

        return [
            Recommendation(
                type=TYPE_NOTIFICATION,
                title=f"{context.current_streak}-session streak on {context.habit_name}",
                content=(
                    f"You have completed {context.current_streak} {context.habit_name} "
                    f"sessions in a row. Keep it up!"
                ),
            )
            for context in on_streak
        ]
