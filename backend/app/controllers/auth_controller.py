from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.security import SecurityService
from db.database import get_db
from repositories.user_repository import UserRepository
from services.auth_service import AuthService
from services.jwt_service import JWTService
from schemas.user_schema import RegisterRequest, LoginRequest, UserResponse, TokenResponse

SECRET_KEY = "***REMOVED***"

# DEPENDENCIAS

def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    repo = UserRepository(session=db)
    jwt_svc = JWTService(secret_key=SECRET_KEY)
    sec_svc = SecurityService()
    return AuthService(
        user_repo=repo, 
        jwt_service=jwt_svc, 
        security_service=sec_svc
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