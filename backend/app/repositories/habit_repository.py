from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.habit import Habit

class HabitRepository:

    def __init__(self, session: Session):
        self.session = session

    # Crea el hábito, lo añade a Session, lo commitea a la BD y lo devuelve con su id
    def create_habit(
        self,
        user_id: int,
        name: str,
        type: Optional[str],
        importance: int
    ) -> Habit:
        new_habit = Habit(
            user_id=user_id,
            name=name,
            type=type,
            importance=importance
        )
        self.session.add(new_habit)
        self.session.commit()
        self.session.refresh(new_habit)
        return new_habit

    # Devuelve todos los hábitos de un usuario (ordenados por id)
    def get_by_user(self, user_id: int) -> list[Habit]:
        stmt = select(Habit).where(Habit.user_id == user_id).order_by(Habit.id)
        return list(self.session.scalars(stmt).all())

    # Devuelve un hábito por id
    def get_by_id(self, habit_id: int) -> Optional[Habit]:
        return self.session.get(Habit, habit_id)

    # Edita un hábito y confirma los cambios
    def update_habit(
        self,
        habit: Habit,
        name: str,
        type: Optional[str],
        importance: int
    ) -> Habit:
        habit.name = name
        habit.type = type
        habit.importance = importance
        self.session.commit()
        self.session.refresh(habit)
        return habit

    # Borra un hábito y confirma los cambios
    def delete_habit(self, habit: Habit) -> None:
        self.session.delete(habit)
        self.session.commit()
