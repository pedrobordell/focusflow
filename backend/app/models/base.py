from sqlalchemy.orm import DeclarativeBase

# Base declarativa compartida por todos los modelos. Cada modelo se registra en
# Base.metadata, que main.py usa para crear las tablas (create_all).
class Base(DeclarativeBase):
    pass
