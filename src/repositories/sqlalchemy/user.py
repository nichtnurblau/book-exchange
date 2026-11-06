from sqlalchemy.orm import Session

from src.database.mappers import UserMapper
from src.database.models import UserRecord
from src.models import User
from src.repositories.user import UserRepository


class SQLAlchemyUserRepository(UserRepository):
    """Хранить пользователей в общей сессии без самостоятельного commit."""

    def __init__(self, session: Session) -> None:
        """Получить сессию от владельца транзакции."""
        self._session = session

    def find_by_login(self, login: str) -> User | None:
        """Искать по нормализованному ключу независимо от регистра."""
        record = self._session.get(UserRecord, login.casefold())
        return UserMapper.to_domain(record) if record is not None else None

    def add(self, user: User) -> None:
        """Добавить запись и проверить ограничения через flush."""
        if self.find_by_login(user.login) is not None:
            raise ValueError("Этот логин уже занят.")
        self._session.add(UserMapper.to_record(user))
        self._session.flush()
