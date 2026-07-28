from typing import Optional

from pydantic import BaseModel

from schemas.statistics_schema import SlotStat

# Objetos INTERNOS del motor de recomendaciones: no entran ni salen por la API (lo que sale
# son Message, ver message_schema). Están aquí, y no dentro del servicio, porque son el
# CONTRATO entre la capa de datos (Pandas) y la capa de estrategia:
#
#   capa de datos  --(list[HabitContext])-->  estrategia  --(list[Recommendation])-->  persistencia
#
# Gracias a ese contrato la estrategia no sabe nada de SQLAlchemy ni de FastAPI: recibe
# números y devuelve textos. Eso permite probarla sin base de datos y, en el futuro,
# sustituir las reglas por un modelo predictivo sin tocar nada más.


# Fotografía de un hábito lista para razonar sobre ella.
class HabitContext(BaseModel):
    habit_id: int
    habit_name: str
    importance: int                             # 1..3, tal cual la define el usuario
    analysis_days: int                          # tamaño de la ventana de cumplimiento, en días
    scheduled: int                              # sesiones programadas en la ventana de análisis
    completed: int                              # cumplidas en la ventana de análisis
    compliance_rate: float                      # completed / scheduled, en [0, 1]
    days_since_last_completed: Optional[int]    # None si nunca ha cumplido ninguna sesión
    days_since_last_session: Optional[int]      # None si no tiene ninguna sesión ya pasada
    current_streak: int                         # sesiones consecutivas cumplidas (las más recientes)
    ever_scheduled: bool                        # False si el hábito no tiene ninguna sesión
    slots: list[SlotStat]                       # métricas por franja de TODO el histórico
    best_slot: Optional[SlotStat]               # franja recomendable; None si no hay muestra suficiente


# Mensaje que propone la estrategia. Todavía no es una fila de la BD: el servicio decide
# si persistirlo (puede estar repetido) y lo convierte en Message.
class Recommendation(BaseModel):
    type: str                                   # 'recommendation' | 'notification'
    title: str
    content: str
