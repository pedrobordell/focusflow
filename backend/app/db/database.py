import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Generator

# Carga las variables de entorno desde backend/.env
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

URL = os.getenv("DATABASE_URL")
if not URL:
    raise RuntimeError(
        "DATABASE_URL no está definida. Copia .env.example a .env y configúrala."
    )

engine = create_engine(URL, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
