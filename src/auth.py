import re

from models import User
from repositories import UserRepository
from security import PasswordHasher


class AuthService:
    """Реализовать регистрацию и управление одной консольной сессией."""

    def __init__(self, repository: UserRepository, hasher: PasswordHasher) -> None:
        """Получить хранилище и средство хеширования извне."""
        self._repository = repository
        self._hasher = hasher
        self._current_user: User | None = None

    @property
    def current_user(self) -> User | None:
        """Вернуть пользователя текущей сессии или None для гостя."""
        return self._current_user

    def register(self, login: str, password: str, name: str, city: str, contact: str) -> User:
        """Проверить все поля Ф1 и создать запись без автоматического входа."""
        login = login.strip()
        if re.fullmatch(r"[A-Za-z0-9_]{3,30}", login) is None:
            raise ValueError("Логин: 3–30 латинских букв, цифр или знаков подчёркивания.")
        if not 8 <= len(password) <= 128 or not password.strip():
            raise ValueError("Пароль: 8–128 символов, не только пробелы.")
        fields = [("Имя", name, 50), ("Город", city, 80), ("Контакт", contact, 100)]
        for label, value, limit in fields:
            if not 1 <= len(value.strip()) <= limit:
                raise ValueError(f"{label}: от 1 до {limit} символов, не только пробелы.")
        if self._repository.find_by_login(login) is not None:
            raise ValueError("Этот логин уже занят.")
        password_hash, salt = self._hasher.create(password)
        user = User(login, name.strip(), city.strip(), contact.strip(), password_hash, salt)
        self._repository.add(user)
        return user

    def login(self, login: str, password: str) -> User:
        """Начать сессию при верных данных; ошибочный вход оставляет гостя."""
        self._current_user = None
        user = self._repository.find_by_login(login.strip())
        if user is None or not self._hasher.verify(password, user.password_hash, user.salt):
            raise ValueError("Неверный логин или пароль.")
        self._current_user = user
        return user

    def logout(self) -> None:
        """Завершить текущую сессию."""
        self._current_user = None

    def require_user(self) -> User:
        """Проверить авторизацию перед действием зарегистрированного пользователя."""
        if self._current_user is None:
            raise PermissionError("Сначала войдите в учётную запись.")
        return self._current_user
