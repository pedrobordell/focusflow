from typing import Optional

from pydantic import BaseModel, Field

# Valida la request para crear un hábito
class HabitCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    # 'type' es opcional porque su dominio aún no está cerrado
    type: Optional[str] = Field(default=None, max_length=50)
    # Importancia en rango 1-3
    importance: int = Field(ge=1, le=3)

# Valida la request para editar un hábito
class HabitUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: Optional[str] = Field(default=None, max_length=50)
    importance: int = Field(ge=1, le=3)

# Response de la API para los hábitos
class HabitResponse(BaseModel):
    id: int
    user_id: int
    name: str
    type: Optional[str]
    importance: int
    model_config = {"from_attributes": True}
