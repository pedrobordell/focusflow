from models.message import Message
from repositories.message_repository import MessageRepository


# Bandeja de entrada: consultar, marcar como leído y borrar los mensajes que el sistema ha
# generado. La GENERACIÓN vive aparte, en RecommendationService; aquí solo se gestionan los
# mensajes ya existentes.
class MessageService:

    # Recibe el MessageRepository
    def __init__(self, message_repo: MessageRepository):
        self.message_repo = message_repo

    # Lista los mensajes del usuario (los más recientes primero)
    def list_messages(self, user_id: int) -> list[Message]:
        return self.message_repo.get_by_user(user_id)

    # Obtiene un mensaje comprobando que pertenece al usuario.
    # Si no existe o no es suyo -> ValueError que el controller traduce a 404. Mismo criterio
    # que en hábitos y sesiones: no se distingue "no existe" de "no es tuyo" para no revelar
    # la existencia de mensajes ajenos.
    def get_message(self, message_id: int, user_id: int) -> Message:
        message = self.message_repo.get_by_id(message_id)
        if message is None or message.user_id != user_id:
            raise ValueError("Message not found")
        return message

    # Marca/desmarca como leído un mensaje propio
    def set_read(self, message_id: int, user_id: int, is_read: bool) -> Message:
        message = self.get_message(message_id, user_id)
        return self.message_repo.update_is_read(message, is_read)

    # Borra un mensaje propio
    def delete_message(self, message_id: int, user_id: int) -> None:
        message = self.get_message(message_id, user_id)
        self.message_repo.delete_message(message)
