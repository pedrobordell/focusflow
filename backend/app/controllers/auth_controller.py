import os
from pathlib import Path
from dotenv import load_dotenv

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from core.security import SecurityService
from db.database import get_db
from models.user import User
from repositories.user_repository import UserRepository
from services.auth_service import AuthService
from services.jwt_service import JWTService
from schemas.user_schema import RegisterRequest, LoginRequest, UserResponse, TokenResponse, LogoutResponse

# Carga las variables de entorno desde backend/.env
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY no está definida. Configúrala en el archivo .env del backend."
    )

# DEPENDENCIAS

# Pide una Session, monta el repo con ella y crea los servicios
def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    repo = UserRepository(session=db)
    jwt_svc = JWTService(secret_key=SECRET_KEY)
    sec_svc = SecurityService()
    return AuthService(
        user_repo=repo,
        jwt_service=jwt_svc,
        security_service=sec_svc
    )

# Lee el token del header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Extrae el token, pide al servicio el usuario y develve el user
def get_current_user(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    try:
        return auth_service.get_user_by_token(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

# CONTROLLER

auth_controller = APIRouter(prefix="/auth", tags=["Authentication"])

# Recibe datos, valida con AuthService y devuelve el usuario
@auth_controller.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    request: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    try:
        user = auth_service.register(
            username=request.username,
            email=request.email,
            password=request.password
        )
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# Recibe datos, valida con AuthService y devuelve JWT
@auth_controller.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    try:
        token = auth_service.login(
            email=request.email,
            password=request.password
        )
        return TokenResponse(access_token=token, token_type="bearer")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

# Devuelve el perfil del usuario autenticado a partir del token
@auth_controller.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
def me(current_user: User = Depends(get_current_user)):
    return current_user

@auth_controller.post("/logout", response_model=LogoutResponse, status_code=status.HTTP_200_OK)
def logout(current_user: User = Depends(get_current_user)):
    return {"message": "Logout successful"}
