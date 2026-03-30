from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Generator

URL = "todo:///mysql"

engine = create_engine(
    URL,
    connect_args={"check_same_thread": False},
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()