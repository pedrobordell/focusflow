from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.user import User
    from models.habit_session import HabitSession

class Habit(Base):
    __tablename__ = "habits"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # El dominio de 'type' aún no está cerrado -> String flexible (validación futura en Pydantic).
    type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    importance: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relaciones
    user: Mapped["User"] = relationship(back_populates="habits")
    sessions: Mapped[list["HabitSession"]] = relationship(
        back_populates="habit", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Habit(id={self.id}, name='{self.name}', importance={self.importance})>"
