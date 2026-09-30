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


# Una sesión pasada reducida a las variables que entiende un modelo.
class SessionFeature(BaseModel):
    slot: int                                   # franja horaria 0-3
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
    sessions: list[SessionFeature] = []         # Sesiones pasadas, una a una, con las variables que 
                                                # usa el modelo, la de reglas las ignora


# Mensaje que propone la estrategia.
class Recommendation(BaseModel):
    type: str
    title: str
    content: str


# Diagnóstico de un hábito hecho por el modelo
class HabitInsight(BaseModel):
    habit_id: int
    habit_name: str
    state: str                                  # abandoned|at_risk|improving|on_track|unknown
    probability: Optional[float]                # P(cumplir) tal y como lo programa AHORA
    trend: float                                # pendiente de la regresión (+ mejora, - empeora)
    trend_label: str                            # Interpretación de la pendiente ("Trending up"/"down"/"Steady")
    current_label: Optional[str]                # Día + Franja actual
    best_slot: Optional[int]
    best_weekday: Optional[int]
    best_probability: Optional[float]           # P(cumplir) en la combinación propuesta
    best_label: Optional[str]                   # Día + Franja propuesta
