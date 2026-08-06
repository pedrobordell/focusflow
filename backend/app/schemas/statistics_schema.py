from datetime import date
from typing import Optional

from pydantic import BaseModel

# Schemas de salida del subsistema de Estadísticas. Son agregados calculados (no mapean
# directamente una fila del ORM), por eso NO usan from_attributes: el service los construye.


# Resumen mínimo de cumplimiento de un periodo. Lo consume el widget del dashboard
# (solo lee compliance_rate); scheduled/completed acompañan como contexto del ratio.
class ComplianceSummary(BaseModel):
    scheduled: int                  # sesiones programadas en el periodo
    completed: int                  # sesiones cumplidas (completed=true)
    compliance_rate: float          # completed / scheduled, en [0, 1]


# Punto de la serie diaria (Weekly Stats, gráfica izquierda: % por día del último mes).
class DayPoint(BaseModel):
    date: date
    compliance_rate: float


# Punto de la serie por hora del día (Habit Stats, gráfica izquierda).
class HourPoint(BaseModel):
    hour: int                       # hora de inicio, 0..23
    compliance_rate: float


# Etiquetas de las 4 franjas horarias (índice 0..3). Viven aquí, en los schemas, y no en el
# service porque las necesitan tanto la capa de datos como la estrategia de recomendación, y
# esta última debe poder importarlas SIN arrastrar SQLAlchemy: un módulo de schemas es puro.
SLOT_LABELS = ["Early morning", "Morning", "Afternoon", "Evening"]


# Métrica de una franja horaria (0-6 / 6-12 / 12-18 / 18-24) de un hábito.
# La consumen tanto Estadísticas ("Best time slot") como el motor de Recomendaciones
# (propuesta de horario de RF14): un único criterio para toda la aplicación.
class SlotStat(BaseModel):
    slot: int                       # índice de la franja, 0..3
    label: str                      # etiqueta legible ("Morning", ...)
    scheduled: int                  # sesiones programadas en esa franja
    completed: int                  # sesiones cumplidas en esa franja
    compliance_rate: float          # completed / scheduled, en [0, 1] (dato observado)
    probability: float              # P(cumplir) suavizada (Laplace), en [0, 1] (estimación)


# Destacado "hábito + valor" para el panel de Weekly Stats.
class HabitHighlight(BaseModel):
    habit_id: int
    habit_name: str
    compliance_rate: float          # % del hábito esa semana
    completed_hours: float          # horas dedicadas (Σ duración de sesiones cumplidas)


# Destacados de la semana (Weekly Stats, panel derecho): semana actual vs anterior.
class WeeklyHighlights(BaseModel):
    week_from: date                 # lunes de la semana analizada
    week_to: date                   # domingo de la semana analizada
    most_hours: Optional[HabitHighlight]        # hábito con más horas dedicadas; None si semana vacía
    worst_compliance: Optional[HabitHighlight]  # hábito con peor % (≥1 sesión); None si semana vacía
    compliance_now: float           # % global de esta semana
    compliance_prev: float          # % global de la semana anterior
    improvement_pp: float           # (now - prev) * 100, en puntos porcentuales


# Detalle de un hábito (Habit Stats, panel derecho).
class HabitDetail(BaseModel):
    habit_id: int
    habit_name: str
    type: Optional[str]
    importance: int
    last10_rate: Optional[float]    # % de las últimas 10 sesiones (fecha ≤ hoy); None si 0 sesiones
    last10_count: int               # nº de sesiones consideradas (≤ 10)
    best_slot: Optional[str]        # franja horaria con mayor %; None si no hay datos en el periodo
