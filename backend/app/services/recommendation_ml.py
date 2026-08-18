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

MIN_TRAINING_SESSIONS = 20      # Sesiones mínimas para entrenar
MAX_DEPTH = 3                   # Profundidad máxima del árbol
MIN_SAMPLES_LEAF = 5            # Mínimo mínmo de sesiones por hojas
RANDOM_STATE = 42               # Semilla de aleatoriedad para que siempre se generen los mismos
                                # mensajes y no se generen otros nuevos ligeramente distintos
RISK_PROBABILITY = 0.5          # Probabilidad para considerar a un hábito en riesgo
TREND_EPSILON = 0.005           # Margen para considerar a una pendiente plana. Es un 15% al mes 
                                # (0.005*30) porque las pendientes están en cumplimiento día
FEATURES = ["slot", "weekday", "importance", "duration"]    # Variables del modelo
WEEKDAY_LABELS = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
]

# --- Estados de un hábito ---------------------------------------------------

STATE_ABANDONED = "abandoned"       # >14 días sin cumplirse
STATE_AT_RISK = "at_risk"           # <50% cumplimiento y con pendiente negativa
STATE_IMPROVING = "improving"       # <50% cumplimiento y con pendiente positiva
STATE_ON_TRACK = "on_track"         # >50% cumplimiento y con pendiente no negativa
STATE_UNKNOWN = "unknown"           # sin datos

# Importancia para generar la recomendación
STATE_SEVERITY = {
    STATE_ABANDONED: 0,
    STATE_AT_RISK: 1,
    STATE_IMPROVING: 2,
    STATE_ON_TRACK: 3,
}

# 0.75 -> "75%"
def _percent(rate: float) -> str:
    return f"{round(rate * 100)}%"


# Une las etiquetas de día y de franja, si no hay día, devuelve solo la franja.
def combination_label(slot: int, weekday: Optional[int]) -> str:
    if weekday is None:
        return f"the {SLOT_LABELS[slot].lower()} slot"
    return f"{WEEKDAY_LABELS[weekday]} {SLOT_LABELS[slot].lower()}"


# Calcula la moda de una lista. En caso de empate escoge el valor más pequeño,
# para no dejar nada al azar.
def _mode(values: list) -> int:
    counts = Counter(values)
    return min(counts, key=lambda value: (-counts[value], value))


# --- Entrenamiento ----------------------------------------------------------

# Escribe todas las sesiones de TODOS los hábitos en un DataFrame con una fila por sesión. 
# No se agrupan por hábitos, sino por la importancia de este.
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


# Crea un árbol de decisión, lo entrena con las columnas FEATURES del DataFrame
# para la variable objetivo "completed" y devuelve el árbol entrenado.
# En caso de que no pueda entrenar (pocas sesiones ó todas las sesiones con el mismo 
# valor en la columna completed), devuelve None.
def train_tree(contexts: list[HabitContext]) -> Optional[DecisionTreeClassifier]:
    df = training_frame(contexts)
    if len(df) < MIN_TRAINING_SESSIONS or df["completed"].nunique() < 2:
        return None
    return new_tree().fit(df[FEATURES], df["completed"])


# Árbol SIN entrenar con los hiperparámetros del proyecto.
def new_tree() -> DecisionTreeClassifier:
    return DecisionTreeClassifier(
        max_depth=MAX_DEPTH,
        min_samples_leaf=MIN_SAMPLES_LEAF,
        random_state=RANDOM_STATE,
    )


# Tendencia del hábito: pendiente de la regresión.
# Positiva = cada vez cumple más; negativa = lo está dejando.
# Con sesiones de un solo día se considera plana.
def trend(sessions: list[SessionFeature]) -> float:
    # Extrae el day_index de todas las sesiones y elimina los duplicados,
    # si todas ocurrieron en un mismo día, se considera plana.
    if len({session.day_index for session in sessions}) < 2:
        return 0.0

    days = np.array([[session.day_index] for session in sessions], dtype=float)
    completed = np.array([int(session.completed) for session in sessions], dtype=float)
    # Extrae la pendiente de la variable days
    return float(LinearRegression().fit(days, completed).coef_[0])


# --- Predicción -------------------------------------------------------------

# Devuelve el Array con la p(cumplir) para una lista de combinaciones (franja, día) de un mismo hábito.
def _predict(tree, combinations: list, importance: int, duration: float) -> np.ndarray:
    # Crea un DataFrame con todas las combinaciones entre slot y weekday con
    # importance y duration dadas por los parámetros
    frame = pd.DataFrame(
        [
            {"slot": slot, "weekday": weekday, "importance": importance, "duration": duration}
            for slot, weekday in combinations
        ],
        columns=FEATURES,
    )

    # Obtiene el id numérico del nodo hoja en el que termina cada fila del DF
    leaves = tree.apply(frame)

    # Array con el nº total de sesiones de cada nodo hoja
    sessions = tree.tree_.n_node_samples[leaves]
    # Array con el nº total de sesiones de cada nodo hoja completadas.
    # leaves: qué nodos mirar, coger el output en la posición 0 (completed) que 
    # haya sido completado (1 true)
    completed = np.rint(tree.tree_.value[leaves, 0, 1] * sessions)
    # Se aplica el suavizado de Laplace
    return (completed + 1) / (sessions + 2)


# Devuelve la mayor probabilidad y su combinación
# Solo se usan las franjas y los días que el usuario haya usado en algún momento.
def _best_combination(tree, importance: int, duration: float, observed: tuple) -> tuple:
    slots, weekdays = observed
    # Producto cartesiano de los slots y los weekday
    combinations = [(slot, weekday) for slot in slots for weekday in weekdays]

    probabilities = _predict(tree, combinations, importance, duration)
    best = int(np.argmax(probabilities))
    best_slot, best_weekday = combinations[best]

    # Obtiene las probabilidades de cumplimiento de la mejor franja sin duplicados,
    # emparejando la combination con su probabilidad.
    same_slot = {
        probability
        for (slot, _), probability in zip(combinations, probabilities)
        if slot == best_slot
    }
    # Si es 1 significa que la probabilidad es la misma en todos los slots de los días
    # (eliminaba duplicados)
    if len(same_slot) == 1:
        best_weekday = None

    return best_slot, best_weekday, float(probabilities[best])


# Devuelve los índices de las franjas y días que el usuario ha usado alguna vez.
# Si no hubiera ninguna asmue que puede usar todos.
def observed_combinations(contexts: list[HabitContext]) -> tuple:
    slots = sorted({session.slot for context in contexts for session in context.sessions})
    weekdays = sorted({session.weekday for context in contexts for session in context.sessions})
    return (
        slots or list(range(len(SLOT_LABELS))),
        weekdays or list(range(len(WEEKDAY_LABELS))),
    )


# Traduce la pendiente a texto, usando el MISMO umbral que la clasificación.
def _trend_label(slope: float) -> str:
    if slope > TREND_EPSILON:
        return "Trending up"
    if slope < -TREND_EPSILON:
        return "Trending down"
    return "Steady"


# Clasifica el hábito en función de lo que predice el árbol (dónde está) y la tendencia (hacia dónde va)
def _classify(context: HabitContext, probability: float, slope: float) -> str:
    days_idle = context.days_since_last_completed
    if days_idle is None or days_idle >= FORGOTTEN_DAYS:
        return STATE_ABANDONED

    if probability < RISK_PROBABILITY:
        return STATE_IMPROVING if slope > TREND_EPSILON else STATE_AT_RISK

    return STATE_AT_RISK if slope < -TREND_EPSILON else STATE_ON_TRACK


# --- Estrategia -------------------------------------------------------------

# No sustituye a las reglas: Reemplaza únicamente la recomendación (el consejo del día)
# y delega en ellas los avisos de hábito olvidado y de racha.
class MLRecommendationStrategy(RecommendationStrategy):

    def __init__(self, fallback: RulesRecommendationStrategy):
        self.fallback = fallback

    def generate(self, contexts: list[HabitContext]) -> list[Recommendation]:
        tree = train_tree(contexts)

        # Si no hay suficientes sesiones, responde con las reglas
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

    # Diagnóstico de todos los hábitos. Esta parte es pública porque lo consume también el endpoint
    # GET /recommendations/insights y la gráfica del árbol.
    def insights(self, contexts: list[HabitContext], tree=None) -> list[HabitInsight]:
        tree = tree if tree is not None else train_tree(contexts)
        observed = observed_combinations(contexts)
        return [self._insight(context, tree, observed) for context in contexts]

    # --- Interior -----------------------------------------------------------

    def _insight(self, context: HabitContext, tree, observed: tuple) -> HabitInsight:
        # Sin modelo o sin sesiones no hay nada que predecir devuelve "unknown"
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

        # Obtiene el slot y el día de la semana más habituales (la moda)
        slot = _mode([session.slot for session in context.sessions])
        weekday = _mode([session.weekday for session in context.sessions])

       # Como duration es continua, para simplificar se usa la MEDIANA del hábito.
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

    # Redacta el consejo del día a partir del estado. Cada estado tiene su acción correctiva
    @staticmethod
    def _message(insight: HabitInsight, context: HabitContext) -> Recommendation:
        name = insight.habit_name

        # Cuando el usuario ya está usando la mejor combinación que encuentra el modelo
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

        # Un estado en riesgo puede ser un estado con la probabilidad baja, 
        # o con probabilidad alta con tendencia bajando, cada uno tiene que tener su explicación.
        elif insight.state == STATE_AT_RISK:
            title = f"{name} is at risk"
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
