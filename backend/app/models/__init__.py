# Importar el paquete 'models' registra Base y todos los modelos en Base.metadata,
# de modo que create_all (en main.py y en los tests) ve las 4 tablas.
from models.base import Base
from models.user import User
from models.habit import Habit
from models.habit_session import HabitSession
from models.message import Message

__all__ = ["Base", "User", "Habit", "HabitSession", "Message"]
