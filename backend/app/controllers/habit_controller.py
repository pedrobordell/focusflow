from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from controllers.auth_controller import get_current_user
from db.database import get_db
from models.user import User
from repositories.habit_repository import HabitRepository
from services.habit_service import HabitService
from schemas.habit_schema import HabitCreateRequest, HabitUpdateRequest, HabitResponse

# DEPENDENCIAS

# Pide una Session (de la BD), monta el repo con ella y crea el servicio
def get_habit_service(db: Session = Depends(get_db)) -> HabitService:
    repo = HabitRepository(session=db)
    return HabitService(habit_repo=repo)

# CONTROLLER

habit_controller = APIRouter(prefix="/habits", tags=["Habits"])

# Crea un hábito para el usuario.
# Autentica el usuario mediante el user_id del token, no del body
@habit_controller.post("", response_model=HabitResponse, status_code=status.HTTP_201_CREATED)
def create_habit(
    request: HabitCreateRequest,
    current_user: User = Depends(get_current_user),
    habit_service: HabitService = Depends(get_habit_service)
):
    habit = habit_service.create_habit(
        user_id=current_user.id,
        name=request.name,
        type=request.type,
        importance=request.importance
    )
    return habit

# Lista los hábitos del usuario autenticado
@habit_controller.get("", response_model=list[HabitResponse], status_code=status.HTTP_200_OK)
def list_habits(
    current_user: User = Depends(get_current_user),
    habit_service: HabitService = Depends(get_habit_service)
):
    return habit_service.list_habits(current_user.id)

# Obtiene un hábito propio (para precargar el formulario de edición)
@habit_controller.get("/{habit_id}", response_model=HabitResponse, status_code=status.HTTP_200_OK)
def get_habit(
    habit_id: int,
    current_user: User = Depends(get_current_user),
    habit_service: HabitService = Depends(get_habit_service)
):
    try:
        return habit_service.get_habit(habit_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

# Actualiza un hábito propio
@habit_controller.put("/{habit_id}", response_model=HabitResponse, status_code=status.HTTP_200_OK)
def update_habit(
    habit_id: int,
    request: HabitUpdateRequest,
    current_user: User = Depends(get_current_user),
    habit_service: HabitService = Depends(get_habit_service)
):
    try:
        return habit_service.update_habit(
            habit_id=habit_id,
            user_id=current_user.id,
            name=request.name,
            type=request.type,
            importance=request.importance
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

# Borra un hábito propio
@habit_controller.delete("/{habit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_habit(
    habit_id: int,
    current_user: User = Depends(get_current_user),
    habit_service: HabitService = Depends(get_habit_service)
):
    try:
        habit_service.delete_habit(habit_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
