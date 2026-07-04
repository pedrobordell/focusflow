from typing import Optional

from sqlalchemy.orm import Session

from models.habit_session import HabitSession

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

    # Edita una Session y confirma los cambios
    def update_session(
        self,
        habit_session: HabitSession,
        habit_id: int,
        date,
        start_time,
        end_time
    ) -> HabitSession:
        habit_session.habit_id = habit_id
        habit_session.date = date
        habit_session.start_time = start_time
        habit_session.end_time = end_time
        self.session.commit()
        self.session.refresh(habit_session)
        return habit_session
