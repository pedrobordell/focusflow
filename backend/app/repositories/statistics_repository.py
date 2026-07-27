from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.habit_session import HabitSession
from models.habit import Habit


# Trae las filas que Pandas va a agregar
class StatisticsRepository:

    def __init__(self, session: Session):
        self.session = session

    # Columnas que consumen los agregadores del service
    _COLUMNS = (
        HabitSession.habit_id,
        Habit.name.label("habit_name"),
        HabitSession.date,
        HabitSession.end_date,
        HabitSession.start_time,
        HabitSession.end_time,
        HabitSession.completed,
    )

    # Devuelve las sesiones del usuario dentro de un rango
    def get_sessions_for_stats(
        self,
        user_id: int,
        date_from: date,
        date_to: date
    ) -> list:
        stmt = (
            select(*self._COLUMNS)
            .join(Habit, HabitSession.habit_id == Habit.id)
            .where(
                Habit.user_id == user_id,
                HabitSession.date >= date_from,
                HabitSession.date <= date_to,
            )
            .order_by(HabitSession.date, HabitSession.start_time)
        )
        return list(self.session.execute(stmt).all())

    # Devuelve las sesiones de un hábito concreto del usuario dentro de un rango
    def get_sessions_for_habit(
        self,
        user_id: int,
        habit_id: int,
        date_from: date,
        date_to: date
    ) -> list:
        stmt = (
            select(*self._COLUMNS)
            .join(Habit, HabitSession.habit_id == Habit.id)
            .where(
                Habit.user_id == user_id,
                HabitSession.habit_id == habit_id,
                HabitSession.date >= date_from,
                HabitSession.date <= date_to,
            )
            .order_by(HabitSession.date, HabitSession.start_time)
        )
        return list(self.session.execute(stmt).all())

    # Estado 'completed' de las últimas N sesiones más recientes ya ocurridas
    # de un hábito concreto del usuario, ordenadas de la más nueva a la más antigua
    def get_recent_completed_for_habit(
        self,
        user_id: int,
        habit_id: int,
        up_to: date,
        limit: int
    ) -> list:
        stmt = (
            select(HabitSession.completed)
            .join(Habit, HabitSession.habit_id == Habit.id)
            .where(
                Habit.user_id == user_id,
                HabitSession.habit_id == habit_id,
                HabitSession.date <= up_to,
            )
            .order_by(HabitSession.date.desc(), HabitSession.start_time.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())
