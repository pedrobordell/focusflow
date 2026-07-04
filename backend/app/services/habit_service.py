from typing import Optional

from models.habit import Habit
from repositories.habit_repository import HabitRepository

class HabitService:

    # Recibe el HabitRepository
    def __init__(self, habit_repo: HabitRepository):
        self.habit_repo = habit_repo

    # Crea un hábito asociado a un usuario
    def create_habit(
        self,
        user_id: int,
        name: str,
        type: Optional[str],
        importance: int
    ) -> Habit:
        return self.habit_repo.create_habit(
            user_id=user_id,
            name=name,
            type=type,
            importance=importance
        )

    # Lista los hábitos del usuario
    def list_habits(self, user_id: int) -> list[Habit]:
        return self.habit_repo.get_by_user(user_id)

    # Obtiene un hábito comprobando que pertenece al usuario
    # Si no existe o no es suyo -> ValueError que el controller lo traducirá a 404
    def get_habit(self, habit_id: int, user_id: int) -> Habit:
        habit = self.habit_repo.get_by_id(habit_id)
        if habit is None or habit.user_id != user_id:
            raise ValueError("Habit not found")
        return habit

    # Edita un hábito propio
    def update_habit(
        self,
        habit_id: int,
        user_id: int,
        name: str,
        type: Optional[str],
        importance: int
    ) -> Habit:
        habit = self.get_habit(habit_id, user_id)
        return self.habit_repo.update_habit(
            habit,
            name=name,
            type=type,
            importance=importance
        )

    # Borra un hábito propio
    def delete_habit(self, habit_id: int, user_id: int) -> None:
        habit = self.get_habit(habit_id, user_id)
        self.habit_repo.delete_habit(habit)
