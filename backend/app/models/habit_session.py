from datetime import date as date_type, datetime, time
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.habit import Habit

class HabitSession(Base):
    # Cada fila es una ocurrencia PROGRAMADA de un hábito; 'completed' indica si se llevó a cabo.
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    habit_id: Mapped[int] = mapped_column(
        ForeignKey("habits.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date_type] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    # Se permiten varias sesiones por hábito y día -> NO hay UNIQUE(habit_id, date).
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    habit: Mapped["Habit"] = relationship(back_populates="sessions")

    # Duración derivada (NO se almacena): end_time - start_time, expresada en minutos.
    # Si en el futuro hiciera falta agregar duraciones en SQL, migrar a hybrid_property.
    @property
    def duration(self) -> Optional[int]:
        if self.start_time is None or self.end_time is None:
            return None
        ref = date_type.min
        delta = datetime.combine(ref, self.end_time) - datetime.combine(ref, self.start_time)
        return int(delta.total_seconds() // 60)

    def __repr__(self) -> str:
        return (
            f"<HabitSession(id={self.id}, habit_id={self.habit_id}, "
            f"date={self.date}, completed={self.completed})>"
        )
