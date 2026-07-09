from datetime import date, time, datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

# Si 'repeat_until' es None crea una sesión única, si lleva una fecha,
# el servicio crea sesiones todas las semanas hasta esa fecha.
# 'end_date' es la fecha de fin: por defecto = date; para sesiones que cruzan
# medianoche, date + 1.
class SessionSpec(BaseModel):
    date: date
    end_date: Optional[date] = None
    start_time: time
    end_time: time
    repeat_until: Optional[date] = None

    # El instante de fin (end_date + end_time) debe ser posterior al de inicio
    # (date + start_time) y, si hay recurrencia, la fecha límite no puede ser
    # anterior a la fecha de la sesión.
    @model_validator(mode="after")
    def check_consistency(self):
        if self.end_date is None:
            self.end_date = self.date
        if datetime.combine(self.end_date, self.end_time) <= datetime.combine(self.date, self.start_time):
            raise ValueError("end must be after start")
        if self.repeat_until is not None and self.repeat_until < self.date:
            raise ValueError("repeat_until must be on or after the session date")
        return self

# Valida request para crear las sesiones (de un mismo hábito) en lote
class SessionBatchCreateRequest(BaseModel):
    habit_id: int
    sessions: list[SessionSpec] = Field(min_length=1)

# Valida request para editar una sesión
class SessionUpdateRequest(BaseModel):
    habit_id: int
    date: date
    end_date: Optional[date] = None
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def check_times(self):
        if self.end_date is None:
            self.end_date = self.date
        if datetime.combine(self.end_date, self.end_time) <= datetime.combine(self.date, self.start_time):
            raise ValueError("end must be after start")
        return self

# Response de la API para las Sessions
class HabitSessionResponse(BaseModel):
    id: int
    habit_id: int
    date: date
    end_date: date
    start_time: time
    end_time: time
    completed: bool
    model_config = {"from_attributes": True}
