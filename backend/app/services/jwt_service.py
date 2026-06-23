import jwt
from datetime import datetime, timedelta, timezone

class JWTService:

    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.algorithm = "HS256"
        self.expiration_minutes = 60
    
    # Mete en el token el ID del usuario, la caducidad y lo firma
    def generate_jwt(self, user_id: int) -> str:
        expiration = datetime.now(timezone.utc) + timedelta(minutes=self.expiration_minutes)
        payload = {
            "sub": str(user_id),
            "exp": expiration
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    # Comprueba la firma y la caducidad
    def verify_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("The token has expired. Please log in again")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")
   