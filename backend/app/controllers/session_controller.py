from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from controllers.auth_controller import get_current_user
from db.database import get_db
from models.user import User
from repositories.session_repository import SessionRepository
from repositories.habit_repository import HabitRepository
from services.session_service import SessionService
from schemas.session_schema import (
    SessionBatchCreateRequest,
    SessionUpdateRequest,
    HabitSessionResponse,
)

# DEPENDENCIAS

# Pide una Session (de la BD), monta los repos con ella y crea el servicio
def get_session_service(db: Session = Depends(get_db)) -> SessionService:
    session_repo = SessionRepository(session=db)
    habit_repo = HabitRepository(session=db)
    return SessionService(session_repo=session_repo, habit_repo=habit_repo)

# CONTROLLER

session_controller = APIRouter(prefix="/sessions", tags=["Sessions"])

# Crea en lote las sesiones de un hábito propio
@session_controller.post("", response_model=list[HabitSessionResponse], status_code=status.HTTP_201_CREATED)
def create_sessions(
    request: SessionBatchCreateRequest,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service)
):
    try:
        return session_service.create_sessions(
            user_id=current_user.id,
            habit_id=request.habit_id,
            specs=request.sessions
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

# Obtiene una sesión propia (para precargar el formulario de edición)
@session_controller.get("/{session_id}", response_model=HabitSessionResponse, status_code=status.HTTP_200_OK)
def get_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service)
):
    try:
        return session_service.get_session(session_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

# Edita una sesión propia
@session_controller.put("/{session_id}", response_model=HabitSessionResponse, status_code=status.HTTP_200_OK)
def update_session(
    session_id: int,
    request: SessionUpdateRequest,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service)
):
    try:
        return session_service.update_session(
            session_id=session_id,
            user_id=current_user.id,
            habit_id=request.habit_id,
            date=request.date,
            start_time=request.start_time,
            end_time=request.end_time
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
