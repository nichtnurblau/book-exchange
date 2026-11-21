from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from src.database.mappers import UserMapper
from src.database.models import UserRecord
from src.models import User


class UserRepository(ABC):
    """Минимальный договор между сервисом и хранилищем пользователей."""

    @abstractmethod
    def find_by_login(self, login: str) -> User | None:
        """Вернуть пользователя без учёта регистра логина либо None."""
        ...

    @abstractmethod
    def add(self, user: User) -> None:
        """Сохранить пользователя; при занятом логине вызвать ValueError."""
        ...


class InMemoryUserRepository(UserRepository):
    """Хранить учётные записи только до завершения программы."""

    def __init__(self) -> None:
        """Создать пустое хранилище."""
        self._users: dict[str, User] = {}

    def find_by_login(self, login: str) -> User | None:
        """Найти пользователя по нормализованному логину."""
        return self._users.get(login.casefold())

    def add(self, user: User) -> None:
        """Добавить запись, не перезаписывая существующего пользователя."""
        key = user.login.casefold()
        if key in self._users:
            raise ValueError("Этот логин уже занят.")
        self._users[key] = user


class SQLAlchemyUserRepository(UserRepository):
    """SQL-хранилище пользователей."""

    def __init__(self, session: Session, commit_on_add: bool = True) -> None:
        """Получить сессию от владельца транзакции."""
        self._session = session
        self._commit_on_add = commit_on_add

    def find_by_login(self, login: str) -> User | None:
        """Искать по нормализованному ключу независимо от регистра."""
        record = self._session.get(UserRecord, login.casefold())
        return UserMapper.to_domain(record) if record is not None else None

    def add(self, user: User) -> None:
        """Добавить пользователя и сохранить запись в БД."""
        if self.find_by_login(user.login) is not None:
            raise ValueError("Этот логин уже занят.")
        self._session.add(UserMapper.to_record(user))
        if self._commit_on_add:
            self._session.commit()
        else:
            self._session.flush()
