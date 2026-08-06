from schemas.recommendation_schema import HabitContext, Recommendation
from services.recommendation_strategy import RecommendationStrategy

# Umbrales de las reglas.
MIN_WINDOW_SESSIONS = 3         # NºSesiones para analizar un hábito.
FORGOTTEN_DAYS = 14             # NºDías para considerar un hábito olvidado.
STREAK_MIN = 3                  # NºSesiones consecutivas para considerar una racha.

# Tipos de mensaje
TYPE_RECOMMENDATION = "recommendation"      # cambios de conducta
TYPE_NOTIFICATION = "notification"          # información de hecho


# 0.75 -> "75%"
def _percent(rate: float) -> str:
    return f"{round(rate * 100)}%"


# REGLAS sobre las métricas del histórico
#
# Hereda de la interfaz RecommendationStrategy, siguiendo el patrón Strategy, el cuál
# permite añadir nuevas estrategias de recomendaciones sin cambiar código.
class RulesRecommendationStrategy(RecommendationStrategy):

    def generate(self, contexts: list[HabitContext]) -> list[Recommendation]:
        recommendations = []

        # Orden de relevancia: primero la propuesta (lo que el usuario debería hacer),
        # después los avisos. El dashboard muestra el primer elemento de tipo 'recommendation'.
        priority = self._priority_recommendation(contexts)
        if priority is not None:
            recommendations.append(priority)

        recommendations.extend(self.forgotten_notifications(contexts))
        recommendations.extend(self.streak_notifications(contexts))
        return recommendations

    # --- Regla 1: hábito prioritario + propuesta de franja horaria ----------

    # Prioridad = importancia * (1 - cumplimiento) = Hábitos importantes con poco cumplimiento
    @staticmethod
    def _priority_score(context: HabitContext) -> float:
        return context.importance * (1 - context.compliance_rate)

    # Selecciona el hábito sobre el que merece la pena actuar y le propone una franja horaria.
    # None si ningún hábito tiene histórico suficiente.
    def _priority_recommendation(self, contexts: list[HabitContext]):
        candidates = [
            context for context in contexts if context.scheduled >= MIN_WINDOW_SESSIONS
        ]
        if not candidates:
            return None

        # Hábito con mayor puntuación, en caso de empate con mayor importancia y sino por id 
        # para asegurar que siempre devuelva el mismo resultado
        target = max(
            candidates,
            key=lambda context: (self._priority_score(context), context.importance, -context.habit_id),
        )

        name = target.habit_name
        # Si tiene 100% de cumplimiento, cambiar el mensaje.
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
            content += (
                " There are not enough sessions yet to suggest a time slot: "
                "schedule a few more and the estimate will appear here."
            )

        return Recommendation(type=TYPE_RECOMMENDATION, title=title, content=content)

    # --- Regla 2: hábitos olvidados ----------------------------------------

    # Una notificación por cada hábito abandonado, del más olvidado al que menos.
    # Público: la estrategia con modelo delega aquí sus notificaciones en vez de duplicarlas.
    def forgotten_notifications(self, contexts: list[HabitContext]) -> list[Recommendation]:
        never_scheduled = []    # Caso A: no tienen días que comparar, van al final
        forgotten = []          # Casos B y C: (días olvidado, Recommendation)

        for context in contexts:
            name = context.habit_name

            # Caso A: Un hábito del que nunca se ha programado ninguna sesión.
            if not context.ever_scheduled:
                never_scheduled.append(Recommendation(
                    type=TYPE_NOTIFICATION,
                    title=f"You have not scheduled {name} yet",
                    content=(
                        f"{name} has no sessions yet, so there is nothing to track. "
                        f"Plan your first one from the calendar."
                    ),
                ))
                continue

            # Días de referencia: 
            # días desde la última sesión CUMPLIDA o,
            # desde la última que le tocaba (si nunca cumplió ninguna) o, 
            # None (si nunca programó ninguna)
            if context.days_since_last_completed is not None:
                days = context.days_since_last_completed
                never_completed = False
            else:
                days = context.days_since_last_session
                never_completed = True
            if days is None or days < FORGOTTEN_DAYS:
                continue

            # Caso B: Nunca cumplió ninguna sesión programada
            if never_completed:
                content = (
                    f"You have never completed a {name} session, and the last one you "
                    f"scheduled was {days} days ago."
                )

            # Caso C: lo cumplía, pero lleva mucho sin hacerlo.
            else:
                content = f"You haven't completed any {name} session in {days} days."

            forgotten.append((days, Recommendation(
                type=TYPE_NOTIFICATION,
                title=f"You're forgetting {name}",
                content=content,
            )))

        
        # Orden los olvidados por la edad en la que fueron olvidados
        forgotten.sort(key=lambda item: item[0], reverse=True)
        # Recomendación de los olvidados y después la de los sin programar.
        return [recommendation for _, recommendation in forgotten] + never_scheduled

    # --- Regla 3: refuerzo positivo por racha -------------------------------

    # Felicita por las rachas en curso, de la más larga a la más corta.
    # Público por el mismo motivo que forgotten_notifications.
    def streak_notifications(self, contexts: list[HabitContext]) -> list[Recommendation]:
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
