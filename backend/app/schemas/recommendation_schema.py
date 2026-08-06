from typing import Optional

from pydantic import BaseModel

from schemas.statistics_schema import SlotStat

# Objetos INTERNOS del motor de recomendaciones: no entran ni salen por la API (lo que sale
# son los de message_schema). 
# 
# Son el CONTRATO entre la capa de datos (Pandas) y la capa de estrategia
# 
# Gracias a ese contrato la estrategia de recomendaciones no sabe nada de 
# SQLAlchemy ni de FastAPI: recibe números y devuelve textos. 
# 
# Permitiendo en el futuro sustituir las reglas por un modelo predictivo sin tocar nada más.


# Una sesión pasada reducida a las variables que entiende un modelo.
#
# Los agregados (compliance_rate, slots...) le bastan a la estrategia por REGLAS, pero un
# clasificador necesita FILAS INDIVIDUALES: una por sesión, cada una con su etiqueta
# (completed). Por eso HabitContext lleva las dos cosas.
class SessionFeature(BaseModel):
    slot: int                                   # franja horaria 0-3 (mismo criterio que SlotStat)
    weekday: int                                # 0 = lunes ... 6 = domingo
    duration: float                             # minutos
    completed: bool                             # la ETIQUETA que el modelo aprende a predecir
    day_index: int                              # días desde la primera sesión del hábito (tendencia)


# Fotografía de un hábito lista.
class HabitContext(BaseModel):
    habit_id: int
    habit_name: str
    importance: int
    analysis_days: int                          # tamaño de la ventana de cumplimiento, en días
    scheduled: int                              # sesiones programadas en la ventana de análisis
    completed: int                              # nºsesiones cumplidas
    compliance_rate: float                      # completed / scheduled, en [0, 1]
    days_since_last_completed: Optional[int]
    days_since_last_session: Optional[int]
    current_streak: int                         # sesiones consecutivas cumplidas (las más recientes)
    ever_scheduled: bool                        # False si el hábito no tiene ninguna sesión
    slots: list[SlotStat]                       # métricas por franja del histórico
    best_slot: Optional[SlotStat]
    # Sesiones pasadas, una a una. Solo las usa la estrategia con modelo; la de reglas las
    # ignora. Por defecto lista vacía para no romper a quien construya un contexto sin ellas.
    sessions: list[SessionFeature] = []


# Mensaje que propone la estrategia.
class Recommendation(BaseModel):
    type: str
    title: str
    content: str


# Diagnóstico de un hábito hecho por el modelo (RF16).
#
# A diferencia de HabitContext y Recommendation, este SÍ sale por la API
# (GET /recommendations/insights), porque la pantalla "Model" lo pinta tal cual.
# Los campos opcionales son None cuando no se ha podido entrenar (state = "unknown"):
# el sistema prefiere callarse a inventarse una predicción.
class HabitInsight(BaseModel):
    habit_id: int
    habit_name: str
    state: str                                  # abandoned|at_risk|improving|on_track|unknown
    probability: Optional[float]                # P(cumplir) tal y como lo programa AHORA
    trend: float                                # pendiente de la regresión (+ mejora, − empeora)
    # Lectura de la pendiente ya interpretada ("Trending up"/"down"/"Steady"). La decide el
    # backend para que el umbral de "cuánto es una tendencia" viva en un único sitio y no
    # haya que repetirlo en JavaScript.
    trend_label: str
    current_label: Optional[str]                # "Monday evening": su franja/día habituales
    best_slot: Optional[int]
    best_weekday: Optional[int]
    best_probability: Optional[float]           # P(cumplir) en la combinación propuesta
    best_label: Optional[str]                   # "Saturday morning": lo que propone el modelo
