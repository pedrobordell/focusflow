from collections import Counter
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeClassifier

from schemas.recommendation_schema import (
    HabitContext,
    HabitInsight,
    Recommendation,
    SessionFeature,
)
from schemas.statistics_schema import SLOT_LABELS
from services.recommendation_rules import (
    FORGOTTEN_DAYS,
    TYPE_RECOMMENDATION,
    RulesRecommendationStrategy,
)
from services.recommendation_strategy import RecommendationStrategy

# --- Umbrales del modelo ----------------------------------------------------

# Filas mínimas para entrenar. Por debajo de esto el árbol memorizaría el histórico en vez
# de aprender de él, así que se prefiere no entrenar.
MIN_TRAINING_SESSIONS = 20

# Profundidad del árbol. NO es un valor a optimizar: un árbol de 3 niveles se puede leer de
# un vistazo, y eso es justo lo que pide RNF06 (explicabilidad). Un modelo opaco que acertara
# un poco más sería peor para un sistema de APOYO A LA DECISIÓN.
MAX_DEPTH = 3

# Hojas con menos sesiones que esto no se crean: evita ramas que describen un solo día suelto.
MIN_SAMPLES_LEAF = 5

# La semilla fija NO es cosmética: los mensajes se deduplican por (usuario, título, día), así
# que un modelo no determinista generaría duplicados cada vez que se abre el dashboard.
RANDOM_STATE = 42

# Por debajo de esta probabilidad se considera que el hábito está en riesgo.
RISK_PROBABILITY = 0.5

# Pendientes entre -EPSILON y +EPSILON se consideran planas. La pendiente está en
# "cumplimiento por día", así que 0.005 equivale a unos 15 puntos porcentuales al mes: por
# debajo de eso el movimiento es ruido y no merece cambiarle el diagnóstico a un hábito.
TREND_EPSILON = 0.005

# Variables de entrada del modelo. El orden importa: es el de las columnas del DataFrame.
FEATURES = ["slot", "weekday", "importance", "duration"]

WEEKDAY_LABELS = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
]

# --- Estados de un hábito (RF16) --------------------------------------------

STATE_ABANDONED = "abandoned"       # lleva demasiado sin cumplirse
STATE_AT_RISK = "at_risk"           # poca probabilidad de cumplirse, o cayendo
STATE_IMPROVING = "improving"       # todavía flojo, pero remontando
STATE_ON_TRACK = "on_track"         # va bien
STATE_UNKNOWN = "unknown"           # sin datos para diagnosticarlo

# De más grave a menos. Decide sobre qué hábito se escribe la recomendación del día.
STATE_SEVERITY = {
    STATE_ABANDONED: 0,
    STATE_AT_RISK: 1,
    STATE_IMPROVING: 2,
    STATE_ON_TRACK: 3,
}


# 0.75 -> "75%"
def _percent(rate: float) -> str:
    return f"{round(rate * 100)}%"


# "Saturday morning". Une las etiquetas de día y de franja; las de franja se importan de los
# schemas para que Estadísticas y el modelo nombren las franjas igual.
#
# Con weekday=None devuelve solo la franja ("the morning slot"), para cuando el modelo no
# distingue entre días: nombrar uno concreto daría a entender un patrón que no ha aprendido.
def combination_label(slot: int, weekday: Optional[int]) -> str:
    if weekday is None:
        return f"the {SLOT_LABELS[slot].lower()} slot"
    return f"{WEEKDAY_LABELS[weekday]} {SLOT_LABELS[slot].lower()}"


# Valor más repetido de una lista. Empates: gana el menor, para que el resultado no dependa
# del orden en que lleguen las sesiones.
def _mode(values: list) -> int:
    counts = Counter(values)
    return min(counts, key=lambda value: (-counts[value], value))


# --- Entrenamiento ----------------------------------------------------------

# Aplana las sesiones de TODOS los hábitos en una tabla: una fila por sesión.
#
# El modelo es uno por USUARIO, no uno por hábito: con ~25 sesiones por hábito no habría nada
# que aprender. La diferencia entre hábitos entra en el modelo como la variable 'importance'.
def training_frame(contexts: list[HabitContext]) -> pd.DataFrame:
    records = [
        {
            "slot": session.slot,
            "weekday": session.weekday,
            "importance": context.importance,
            "duration": session.duration,
            "completed": int(session.completed),
        }
        for context in contexts
        for session in context.sessions
    ]
    return pd.DataFrame.from_records(records, columns=FEATURES + ["completed"])


# Entrena el árbol con el histórico del usuario. Devuelve None cuando no se puede entrenar,
# y entonces quien llama debe recaer en las reglas.
#
# Son dos los casos en los que no se entrena:
#   1. Pocas sesiones (arranque en frío).
#   2. Todas las sesiones con el mismo 'completed'. Este caso es normal (un hábito que el
#      usuario siempre cumple) y hay que cortarlo aquí: con una sola clase, predict_proba
#      devuelve UNA columna en vez de dos y leer la segunda reventaría con IndexError.
def train_tree(contexts: list[HabitContext]) -> Optional[DecisionTreeClassifier]:
    df = training_frame(contexts)
    if len(df) < MIN_TRAINING_SESSIONS or df["completed"].nunique() < 2:
        return None
    return new_tree().fit(df[FEATURES], df["completed"])


# Árbol SIN entrenar con los hiperparámetros del proyecto. Existe para que la evaluación
# (validación cruzada) mida exactamente el mismo modelo que se usa en producción: si los
# hiperparámetros vivieran en dos sitios, la métrica publicada podría no corresponder.
def new_tree() -> DecisionTreeClassifier:
    return DecisionTreeClassifier(
        max_depth=MAX_DEPTH,
        min_samples_leaf=MIN_SAMPLES_LEAF,
        random_state=RANDOM_STATE,
    )


# Tendencia del hábito: pendiente de la recta que mejor ajusta (día -> cumplida).
# Positiva = el usuario cumple cada vez más; negativa = lo está dejando.
# Con sesiones de un solo día no hay recta que ajustar, así que se considera plana.
def trend(sessions: list[SessionFeature]) -> float:
    if len({session.day_index for session in sessions}) < 2:
        return 0.0

    days = np.array([[session.day_index] for session in sessions], dtype=float)
    completed = np.array([int(session.completed) for session in sessions], dtype=float)
    return float(LinearRegression().fit(days, completed).coef_[0])


# --- Predicción -------------------------------------------------------------

# P(cumplir) para una lista de combinaciones (franja, día) de un mismo hábito.
#
# No se usa predict_proba: se leen los conteos de la hoja en la que cae cada combinación y se
# les aplica LAPLACE, (cumplidas + 1) / (sesiones + 2), el mismo suavizado que la capa de
# datos aplica por franja horaria. Un criterio único en toda la aplicación.
#
# El motivo es que un árbol devuelve la proporción cruda de la hoja: una hoja de 5 sesiones
# todas cumplidas daría "100% de probabilidad", una certeza que 5 sesiones no sostienen.
# Con Laplace esa misma hoja dice 86%, que es lo que de verdad respaldan los datos.
def _predict(tree, combinations: list, importance: int, duration: float) -> np.ndarray:
    frame = pd.DataFrame(
        [
            {"slot": slot, "weekday": weekday, "importance": importance, "duration": duration}
            for slot, weekday in combinations
        ],
        columns=FEATURES,
    )

    leaves = tree.apply(frame)
    # tree_.value guarda PROPORCIONES por clase y n_node_samples el tamaño de la hoja;
    # multiplicando se recuperan los conteos. La columna 1 es la clase "cumplida".
    sessions = tree.tree_.n_node_samples[leaves]
    completed = np.rint(tree.tree_.value[leaves, 0, 1] * sessions)
    return (completed + 1) / (sessions + 2)


# Barre las combinaciones (franja, día) y devuelve la que mayor probabilidad obtiene.
#
# ESTE es el valor que las reglas no pueden dar: las reglas solo saben elegir entre las
# franjas que el usuario ya ha probado PARA ESE HÁBITO, mientras que el árbol puntúa también
# combinaciones nuevas, porque ha aprendido el efecto de cada variable por separado.
#
# Ahora bien, solo se barren las franjas y los días que el usuario usa en ALGÚN momento de su
# histórico. Sin ese filtro el árbol propondría de madrugada con toda la confianza del mundo:
# como no hay ni una sesión que lo contradiga, esa región hereda la probabilidad de la hoja
# vecina. Proponer un horario que el usuario no pisa nunca no es descubrir un patrón, es
# rellenar un hueco.
#
# argmax devuelve el PRIMER máximo y las combinaciones se generan siempre en el mismo orden,
# así que ante un empate sale siempre la misma: el título del mensaje no baila.
def _best_combination(tree, importance: int, duration: float, observed: tuple) -> tuple:
    slots, weekdays = observed
    combinations = [(slot, weekday) for slot in slots for weekday in weekdays]

    probabilities = _predict(tree, combinations, importance, duration)
    best = int(np.argmax(probabilities))
    best_slot, best_weekday = combinations[best]

    # ¿El árbol distingue de verdad entre días dentro de esa franja? Si todos puntúan igual
    # es que no ha llegado a partir por 'weekday', y entonces se propone la franja a secas.
    # Decir "el lunes" cuando el modelo no sabe nada del lunes sería inventarse el motivo.
    same_slot = {
        probability
        for (slot, _), probability in zip(combinations, probabilities)
        if slot == best_slot
    }
    if len(same_slot) == 1:
        best_weekday = None

    return best_slot, best_weekday, float(probabilities[best])


# Franjas y días que el usuario ha usado alguna vez, en cualquiera de sus hábitos.
# Si no hubiera ninguna (no debería, porque entonces no habría modelo), se abre todo.
def observed_combinations(contexts: list[HabitContext]) -> tuple:
    slots = sorted({session.slot for context in contexts for session in context.sessions})
    weekdays = sorted({session.weekday for context in contexts for session in context.sessions})
    return (
        slots or list(range(len(SLOT_LABELS))),
        weekdays or list(range(len(WEEKDAY_LABELS))),
    )


# Traduce la pendiente a algo que se pueda leer en pantalla, usando el MISMO umbral que la
# clasificación: así el texto nunca dice "estable" de algo que el estado considera en caída.
def _trend_label(slope: float) -> str:
    if slope > TREND_EPSILON:
        return "Trending up"
    if slope < -TREND_EPSILON:
        return "Trending down"
    return "Steady"


# Clasifica el hábito cruzando las dos señales: lo que predice el árbol (dónde está) y la
# pendiente de la tendencia (hacia dónde va). Es la "clasificación del estado" que pide RF16.
#
# Manda la probabilidad y la tendencia matiza, no al revés. Si la tendencia mandara, una
# pendiente de -0.003 (ruido) bastaría para marcar "en riesgo" un hábito que el modelo da por
# cumplido, y saldría un mensaje que se contradice a sí mismo.
def _classify(context: HabitContext, probability: float, slope: float) -> str:
    days_idle = context.days_since_last_completed
    if days_idle is None or days_idle >= FORGOTTEN_DAYS:
        return STATE_ABANDONED

    if probability < RISK_PROBABILITY:
        # Flojo. Solo se le concede "mejorando" si está remontando de forma apreciable.
        return STATE_IMPROVING if slope > TREND_EPSILON else STATE_AT_RISK

    # Va bien, pero si además está cayendo con claridad conviene avisar antes de que se tuerza.
    return STATE_AT_RISK if slope < -TREND_EPSILON else STATE_ON_TRACK


# --- Estrategia -------------------------------------------------------------

# Estrategia de recomendación basada en MODELOS LIGEROS (RF16).
#
# No sustituye a las reglas: las COMPONE. Reemplaza únicamente el mensaje de tipo
# 'recommendation' (el consejo del día) y delega en ellas los avisos de hábito olvidado y de
# racha, que son RF15 y se perderían si se cambiara una estrategia por la otra sin más.
#
# Sigue siendo una estrategia PURA: recibe números y devuelve textos, sin saber que existen
# la base de datos ni FastAPI.
class MLRecommendationStrategy(RecommendationStrategy):

    # La estrategia de reglas entra por el constructor porque cumple dos papeles: es el plan
    # B cuando no hay datos para entrenar y es quien sigue redactando las notificaciones.
    def __init__(self, fallback: RulesRecommendationStrategy):
        self.fallback = fallback

    def generate(self, contexts: list[HabitContext]) -> list[Recommendation]:
        tree = train_tree(contexts)

        # Arranque en frío: sin histórico suficiente el sistema NO improvisa, responde con
        # las reglas, que sí saben trabajar con pocos datos.
        if tree is None:
            return self.fallback.generate(contexts)

        insights = self.insights(contexts, tree)

        recommendations = []
        target = self._pick_target(insights, contexts)
        if target is not None:
            insight, context = target
            recommendations.append(self._message(insight, context))

        # Mismo orden de relevancia que la estrategia de reglas: consejo, olvidos, rachas.
        recommendations.extend(self.fallback.forgotten_notifications(contexts))
        recommendations.extend(self.fallback.streak_notifications(contexts))
        return recommendations

    # Diagnóstico de todos los hábitos. Público porque lo consume también el endpoint
    # GET /recommendations/insights y la gráfica del árbol.
    def insights(self, contexts: list[HabitContext], tree=None) -> list[HabitInsight]:
        tree = tree if tree is not None else train_tree(contexts)
        observed = observed_combinations(contexts)
        return [self._insight(context, tree, observed) for context in contexts]

    # --- Interior -----------------------------------------------------------

    def _insight(self, context: HabitContext, tree, observed: tuple) -> HabitInsight:
        # Sin modelo o sin sesiones no hay nada que predecir: se dice "unknown" en vez de
        # rellenar con ceros, que se leerían como "tienes un 0% de cumplirlo".
        if tree is None or not context.sessions:
            return HabitInsight(
                habit_id=context.habit_id,
                habit_name=context.habit_name,
                state=STATE_UNKNOWN,
                probability=None,
                trend=0.0,
                trend_label=_trend_label(0.0),
                current_label=None,
                best_slot=None,
                best_weekday=None,
                best_probability=None,
                best_label=None,
            )

        # Cómo programa HOY el hábito: su franja y su día habituales.
        slot = _mode([session.slot for session in context.sessions])
        weekday = _mode([session.weekday for session in context.sessions])

        # 'duration' es continua, así que el barrido de combinaciones necesita fijarle un
        # valor; se usa la MEDIANA del hábito, es decir, su sesión típica. Es una suposición
        # explícita: comparamos horarios a igualdad de duración.
        duration = float(np.median([session.duration for session in context.sessions]))

        probability = float(_predict(tree, [(slot, weekday)], context.importance, duration)[0])
        slope = trend(context.sessions)
        best_slot, best_weekday, best_probability = _best_combination(
            tree, context.importance, duration, observed
        )

        return HabitInsight(
            habit_id=context.habit_id,
            habit_name=context.habit_name,
            state=_classify(context, probability, slope),
            probability=round(probability, 4),
            trend=round(slope, 6),
            trend_label=_trend_label(slope),
            current_label=combination_label(slot, weekday),
            best_slot=best_slot,
            best_weekday=best_weekday,
            best_probability=round(best_probability, 4),
            best_label=combination_label(best_slot, best_weekday),
        )

    # Elige el hábito sobre el que merece la pena escribir: el que está peor.
    # Desempates fijos (importancia y luego menor id) para que el título sea determinista,
    # igual que hace la estrategia de reglas.
    @staticmethod
    def _pick_target(insights: list[HabitInsight], contexts: list[HabitContext]):
        by_id = {context.habit_id: context for context in contexts}
        candidates = [
            (insight, by_id[insight.habit_id])
            for insight in insights
            if insight.state != STATE_UNKNOWN
        ]
        if not candidates:
            return None

        return min(
            candidates,
            key=lambda pair: (
                STATE_SEVERITY[pair[0].state],
                -pair[1].importance,
                pair[0].habit_id,
            ),
        )

    # Redacta el consejo del día a partir del estado. Cada estado tiene su acción correctiva;
    # el texto cita siempre el dato que la justifica, que es lo que exige RNF06.
    @staticmethod
    def _message(insight: HabitInsight, context: HabitContext) -> Recommendation:
        name = insight.habit_name

        # A veces la mejor combinación que encuentra el modelo es la que el usuario ya usa.
        # Presentarla como "prueba a hacer X" sería absurdo, porque X es lo que hace: en ese
        # caso se le dice que el horario no es el problema.
        if insight.best_label == insight.current_label:
            proposal = (
                f"That is already the best time the model can find for it, so the schedule "
                f"is not what is holding you back."
            )
        else:
            proposal = (
                f"The model suggests {insight.best_label}, where it estimates "
                f"{_percent(insight.best_probability)}."
            )

        if insight.state == STATE_ABANDONED:
            days = context.days_since_last_completed
            when = f"in {days} days" if days is not None else "yet"
            title = f"Restart {name}"
            content = f"You have not completed a {name} session {when}. {proposal}"

        elif insight.state == STATE_AT_RISK:
            title = f"{name} is at risk"
            # Se llega a "en riesgo" por dos caminos distintos y cada uno pide su explicación:
            # o la probabilidad es baja, o es alta pero está cayendo. Un texto único acabaría
            # diciendo algo tan raro como "tienes un 90% y vas mal".
            if insight.probability < RISK_PROBABILITY:
                content = (
                    f"Scheduling {name} on {insight.current_label}, as you usually do, gives "
                    f"you an estimated {_percent(insight.probability)} chance of completing "
                    f"it. {proposal}"
                )
            else:
                content = (
                    f"You still complete {name} often, but your compliance has been going "
                    f"down lately. {proposal}"
                )

        elif insight.state == STATE_IMPROVING:
            title = f"{name} is improving"
            content = (
                f"You are completing {name} more and more often, although the model still "
                f"estimates only {_percent(insight.probability)} on {insight.current_label}. "
                f"{proposal}"
            )

        else:
            title = f"{name} is on track"
            content = (
                f"The model estimates {_percent(insight.probability)} that you will complete "
                f"your next {name} session on {insight.current_label}. Keep it up."
            )

        return Recommendation(type=TYPE_RECOMMENDATION, title=title, content=content)
