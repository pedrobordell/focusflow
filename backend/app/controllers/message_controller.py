from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from controllers.auth_controller import get_current_user
from db.database import get_db
from models.user import User
from repositories.message_repository import MessageRepository
from services.message_service import MessageService
from schemas.message_schema import MessageReadUpdate, MessageResponse

# DEPENDENCIAS

# Pide una Session (de la BD), monta el repo con ella y crea el servicio
def get_message_service(db: Session = Depends(get_db)) -> MessageService:
    repo = MessageRepository(session=db)
    return MessageService(message_repo=repo)

# CONTROLLER

message_controller = APIRouter(prefix="/messages", tags=["Messages"])


# Lista los mensajes del usuario autenticado, del más reciente al más antiguo
@message_controller.get("", response_model=list[MessageResponse], status_code=status.HTTP_200_OK)
def list_messages(
    current_user: User = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service),
):
    return message_service.list_messages(current_user.id)


# Marca/desmarca como leído un mensaje propio (PATCH para actualización parcial)
@message_controller.patch("/{message_id}", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def set_message_read(
    message_id: int,
    request: MessageReadUpdate,
    current_user: User = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service),
):
    try:
        return message_service.set_read(message_id, current_user.id, request.is_read)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# Borra un mensaje propio
@message_controller.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service),
):
    try:
        message_service.delete_message(message_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
