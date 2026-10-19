from abc import ABC, abstractmethod

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
