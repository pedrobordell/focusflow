from typing import Optional
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.habit_session import HabitSession
from models.habit import Habit

class SessionRepository:

    def __init__(self, session: Session):
        self.session = session

    # Inserta varias sesiones de una vez, commitea y las devuelve con su id asignado.
    def create_many(self, sessions: list[HabitSession]) -> list[HabitSession]:
        self.session.add_all(sessions)
        self.session.commit()
        for session in sessions:
            self.session.refresh(session)
        return sessions

    # Devuelve una sesión por su id
    def get_by_id(self, session_id: int) -> Optional[HabitSession]:
        return self.session.get(HabitSession, session_id)

    # Devuelve las sesiones del usuario (a través de JOIN con Habits) dentro de un rango de
    # fechas [date_from, date_to], ordenadas por fecha y hora de inicio.
    def get_by_user_and_range(
        self,
        user_id: int,
        date_from: date,
        date_to: date
    ) -> list[HabitSession]:
        stmt = (
            select(HabitSession)
            .join(Habit, HabitSession.habit_id == Habit.id)
            .where(
                Habit.user_id == user_id,
                HabitSession.date >= date_from,
                HabitSession.date <= date_to,
            )
            .order_by(HabitSession.date, HabitSession.start_time)
        )
        return list(self.session.scalars(stmt).all())

    # Borra una Session y confirma los cambios
    def delete_session(self, habit_session: HabitSession) -> None:
        self.session.delete(habit_session)
        self.session.commit()

    # Edita una Session y confirma los cambios
    def update_session(
        self,
        habit_session: HabitSession,
        habit_id: int,
        date,
        end_date,
        start_time,
        end_time
    ) -> HabitSession:
        habit_session.habit_id = habit_id
        habit_session.date = date
        habit_session.end_date = end_date
        habit_session.start_time = start_time
        habit_session.end_time = end_time
        self.session.commit()
        self.session.refresh(habit_session)
        return habit_session
