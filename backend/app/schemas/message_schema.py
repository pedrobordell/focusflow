from datetime import datetime

from pydantic import BaseModel

# Schemas del subsistema de Recomendaciones y Mensajes. A diferencia de los de Estadísticas,
# estos SÍ mapean una fila del ORM (tabla 'messages'), por eso MessageResponse usa
# from_attributes: FastAPI construye la respuesta leyendo los atributos del objeto Message.


# Actualización parcial: marcar/desmarcar un mensaje como leído.
# Mismo patrón que SessionCompletionUpdate (PATCH con un único campo).
class MessageReadUpdate(BaseModel):
    is_read: bool


# Response de la API para los Message (recomendaciones y notificaciones del sistema).
class MessageResponse(BaseModel):
    id: int
    type: str                       # 'recommendation' (propone) | 'notification' (informa)
    title: str
    content: str
    created_at: datetime
    is_read: bool
    model_config = {"from_attributes": True}
