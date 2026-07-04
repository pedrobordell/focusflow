from datetime import date as date_type, time, timedelta

from models.habit_session import HabitSession
from repositories.session_repository import SessionRepository
from repositories.habit_repository import HabitRepository
from schemas.session_schema import SessionSpec

class SessionService:

    # Recibe el SessionRepository y el HabitRepository (para comprobar propiedad)
    def __init__(self, session_repo: SessionRepository, habit_repo: HabitRepository):
        self.session_repo = session_repo
        self.habit_repo = habit_repo

    # Crea en lote las sesiones de un hábito propio
    def create_sessions(
        self,
        user_id: int,
        habit_id: int,
        specs: list[SessionSpec]
    ) -> list[HabitSession]:
        # Comprueba que el hábito exista y pertenezca al usuario. Si no -> ValueError 
        # y el controller lo traduce a 404
        habit = self.habit_repo.get_by_id(habit_id)
        if habit is None or habit.user_id != user_id:
            raise ValueError("Habit not found")

        rows: list[HabitSession] = []
        for spec in specs:
            # Si no hay recurrencia
            if spec.repeat_until is None:
                rows.append(HabitSession(
                    habit_id=habit_id,
                    date=spec.date,
                    start_time=spec.start_time,
                    end_time=spec.end_time
                ))
            # Si hay recurrencia, añade una Session por semana hasta repeat_until
            else:
                current = spec.date
                while current <= spec.repeat_until:
                    rows.append(HabitSession(
                        habit_id=habit_id,
                        date=current,
                        start_time=spec.start_time,
                        end_time=spec.end_time
                    ))
                    current = current + timedelta(weeks=1)

        return self.session_repo.create_many(rows)

    # Obtiene una Session comprobando la propiedad
    # Si no existe o el hábito no es del usuario -> ValueError y el controller lo traduce a 404
    def get_session(self, session_id: int, user_id: int) -> HabitSession:
        session = self.session_repo.get_by_id(session_id)
        if session is None:
            raise ValueError("Session not found")
        habit = self.habit_repo.get_by_id(session.habit_id)
        if habit is None or habit.user_id != user_id:
            raise ValueError("Session not found")
        return session

    # Edita una Session propia. Permite reasignarla a otro hábito (del usuario)
    def update_session(
        self,
        session_id: int,
        user_id: int,
        habit_id: int,
        date: date_type,
        start_time: time,
        end_time: time
    ) -> HabitSession:
        session = self.get_session(session_id, user_id)
        habit = self.habit_repo.get_by_id(habit_id)
        if habit is None or habit.user_id != user_id:
            raise ValueError("Habit not found")
        return self.session_repo.update_session(
            session,
            habit_id=habit_id,
            date=date,
            start_time=start_time,
            end_time=end_time
        )
