import os

# La app exige SECRET_KEY y DATABASE_URL al importarse. Las fijamos para el entorno de test:
# la BD real se sustituye por SQLite en memoria (no se conecta a MySQL).
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main
from db.database import get_db
from models import Base


@pytest.fixture()
def client():
    # SQLite en memoria compartida por todas las conexiones del test (StaticPool)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(main.app)
    finally:
        main.app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
