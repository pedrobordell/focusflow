from pydantic import BaseModel, EmailStr, Field

# Valida la entrada de un Register
class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr = Field(max_length=100)
    # bcrypt solo usa los primeros 72 bytes de la contraseña
    password: str = Field(min_length=6, max_length=72)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# No incluye contraseña
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    model_config = {"from_attributes": True}

# Devuelto por el login
class TokenResponse(BaseModel):
    access_token: str
    token_type: str

class LogoutResponse(BaseModel):
    message: str
