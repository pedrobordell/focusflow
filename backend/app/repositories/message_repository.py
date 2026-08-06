from datetime import date, datetime, time, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.message import Message


class MessageRepository:

    def __init__(self, session: Session):
        self.session = session

    # Inserta varios mensajes de una vez, commitea y los devuelve con su id asignado.
    def create_many(self, messages: list[Message]) -> list[Message]:
        if not messages:
            return []
        self.session.add_all(messages)
        self.session.commit()
        for message in messages:
            self.session.refresh(message)
        return messages

    # Devuelve todos los mensajes del usuario, del más reciente al más antiguo. En caso de
    # ser generados al mismo tiempo, el id ascendente mantiene el orden de relevancia con 
    # el que los produjo la estrategia.
    def get_by_user(self, user_id: int) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.user_id == user_id)
            .order_by(Message.created_at.desc(), Message.id)
        )
        return list(self.session.scalars(stmt).all())

    # Devuelve los mensajes del usuario en un día concreto.
    def get_by_user_and_day(self, user_id: int, day: date) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.user_id == user_id, *self._created_on(day)) # -> Desempaqueta las dos condiciones
            .order_by(Message.created_at.desc(), Message.id)
        )
        return list(self.session.scalars(stmt).all())

    # Títulos que el usuario ya tiene generados ese día. Es la clave de deduplicación:
    # el servicio no vuelve a insertar un mensaje cuyo título ya exista hoy.
    def get_titles_created_on(self, user_id: int, day: date) -> set[str]:
        stmt = (
            select(Message.title)
            .where(Message.user_id == user_id, *self._created_on(day))
        )
        return set(self.session.scalars(stmt).all())

    # Devuelve un mensaje por su id
    def get_by_id(self, message_id: int) -> Optional[Message]:
        return self.session.get(Message, message_id)

    # Marca/desmarca un mensaje como leído y confirma los cambios
    def update_is_read(self, message: Message, is_read: bool) -> Message:
        message.is_read = is_read
        self.session.commit()
        self.session.refresh(message)
        return message

    # Borra un mensaje y confirma los cambios
    def delete_message(self, message: Message) -> None:
        self.session.delete(message)
        self.session.commit()

    # Helper estático y reutilizable que devuelve dos condiciones que se usan para filtrar en una sentencia
    # where por el rango de tiempo exacto [00:00:00 - 00:00:00 del día siguiente).
    # Es mejor expresarlas como rango, y no como func.date(created_at) == day, porque poner funciones en sentencias
    # where impide al motor de la base de datos usar índices sobre la columna (InnoDB los genera
    # automáticamente para las FK, como user_id)
    @staticmethod
    def _created_on(day: date) -> tuple:
        start = datetime.combine(day, time.min)
        return (
            Message.created_at >= start,
            Message.created_at < start + timedelta(days=1),
        )
