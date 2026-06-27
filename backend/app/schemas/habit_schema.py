from typing import Optional

from pydantic import BaseModel, Field

# Valida la entrada al crear un hábito
class HabitCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    # 'type' es opcional (su dominio aún no está cerrado); coincide con el modelo (nullable).
    type: Optional[str] = Field(default=None, max_length=50)
    # Importancia en la escala 1..3 (1 = Low, 2 = Medium, 3 = High).
    importance: int = Field(ge=1, le=3)

# Valida la entrada al editar un hábito (PUT: reemplaza todos los campos)
class HabitUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: Optional[str] = Field(default=None, max_length=50)
    importance: int = Field(ge=1, le=3)

# Lo que devuelve la API para un hábito
class HabitResponse(BaseModel):
    id: int
    user_id: int
    name: str
    type: Optional[str]
    importance: int
    model_config = {"from_attributes": True}
