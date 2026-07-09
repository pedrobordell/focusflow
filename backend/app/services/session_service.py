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
            # Desplazamiento de la fecha de fin respecto a la de inicio (0 mismo día, 1 si cruza medianoche).
            # El validador del schema garantiza que spec.end_date ya está resuelto.
            end_offset = (spec.end_date - spec.date).days
            # Si no hay recurrencia
            if spec.repeat_until is None:
                rows.append(HabitSession(
                    habit_id=habit_id,
                    date=spec.date,
                    end_date=spec.end_date,
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
                        end_date=current + timedelta(days=end_offset),
                        start_time=spec.start_time,
                        end_time=spec.end_time
                    ))
                    current = current + timedelta(weeks=1)

        return self.session_repo.create_many(rows)

    # Lista las sesiones del usuario dentro de un rango de fechas (para el calendario).
    # La propiedad la garantiza el filtro por Habit.user_id del repositorio.
    def list_sessions(
        self,
        user_id: int,
        date_from: date_type,
        date_to: date_type
    ) -> list[HabitSession]:
        return self.session_repo.get_by_user_and_range(user_id, date_from, date_to)

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

    # Borra una Session propia. get_session ya comprueba la propiedad (ValueError -> 404)
    def delete_session(self, session_id: int, user_id: int) -> None:
        session = self.get_session(session_id, user_id)
        self.session_repo.delete_session(session)

    # Edita una Session propia. Permite reasignarla a otro hábito (del usuario)
    def update_session(
        self,
        session_id: int,
        user_id: int,
        habit_id: int,
        date: date_type,
        end_date: date_type,
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
            end_date=end_date,
            start_time=start_time,
            end_time=end_time
        )
