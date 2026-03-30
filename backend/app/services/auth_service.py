from core.security import SecurityService
from .jwt_service import JWTService
from models.user import User
from repositories.user_repository import UserRepository

class AuthService:

    def __init__(
        self, 
        user_repo: UserRepository, 
        jwt_service: JWTService,
        security_service: SecurityService
    ):
        self.user_repo = user_repo
        self.jwt_service = jwt_service
        self.security_service = security_service
    
    # Valida el usuario, hashea la contraseña y lo guarda en la BD
    def register(self, username: str, email: str, password: str) -> User:
        existing_user = self.user_repo.get_by_email(email)
        if existing_user:
            raise ValueError("The email is already registered")
        hashed_password = self.security_service.hash_password(password)
        new_user = self.user_repo.create_user(
            username=username,
            email=email,
            password=hashed_password
        )
        return new_user
    
    # Valida credenciales y devuelve un JWT
    def login(self, email: str, password: str) -> str:
        user = self.user_repo.get_by_email(email)
        if not user or not self.security_service.verify_password(password, user.password):
            raise ValueError("Invalid credentials")
        return self.jwt_service.generate_jwt(user.id)