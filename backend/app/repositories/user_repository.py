from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional

from models.user import User

class UserRepository:
    
    def __init__(self, session: Session):
        self.session = session

    def create_user(self, username: str, email: str, password: str) -> User:
        new_user = User(
            username=username,
            email=email,
            password=password
        )
        self.session.add(new_user)
        self.session.commit()
        self.session.refresh(new_user)
        return new_user
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.session.get(User, user_id)
    
    def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email)
        return self.session.scalars(stmt).first()