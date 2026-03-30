from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Generator

URL = "mysql+pymysql://root:***REMOVED***@localhost:3306/focusflow"

engine = create_engine(URL, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()