from datetime import datetime

from pydantic import BaseModel

# Schemas del subsistema de Recomendaciones y Mensajes. 
# SÍ mapean una fila del ORM (tabla 'messages'), por eso MessageResponse usa from_attributes

# Actualización parcial: marcar/desmarcar un mensaje como leído.
class MessageReadUpdate(BaseModel):
    is_read: bool

# Response de la API para los Message
class MessageResponse(BaseModel):
    id: int
    type: str
    title: str
    content: str
    created_at: datetime
    is_read: bool
    model_config = {"from_attributes": True}
