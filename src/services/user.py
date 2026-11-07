import re

from src.models import User
from src.repositories.user import UserRepository
from src.security import PasswordHasher


class UserService:
    """Реализовать регистрацию и управление одной консольной сессией."""

    def __init__(self, user_repository: UserRepository, password_hasher: PasswordHasher) -> None:
        """Получить хранилище и средство хеширования извне."""
        self._user_repository = user_repository
        self._password_hasher = password_hasher
        self._current_user: User | None = None

    @property
    def current_user(self) -> User | None:
        """Вернуть пользователя текущей сессии или None для гостя."""
        return self._current_user

    def register(self, login: str, password: str, name: str, city: str, contact: str) -> User:
        """Проверить все поля Ф1 и создать запись без автоматического входа."""
        login = self.validate_login(login)
        password = self.validate_password(password)
        name = self.validate_name(name)
        city = self.validate_city(city)
        contact = self.validate_contact(contact)
        password_hash, salt = self._password_hasher.create(password)
        user = User(login, name, city, contact, password_hash, salt)
        self._user_repository.add(user)
        return user

    def validate_login(self, login: str) -> str:
        """Проверить формат и доступность логина."""
        login = login.strip()
        if re.fullmatch(r"[A-Za-z0-9_]{3,30}", login) is None:
            raise ValueError("Логин: 3–30 латинских букв, цифр или знаков подчёркивания.")
        if self._user_repository.find_by_login(login) is not None:
            raise ValueError("Этот логин уже занят.")
        return login

    @staticmethod
    def validate_password(password: str) -> str:
        """Проверить длину пароля, сохранив пробелы в нём."""
        if not 8 <= len(password) <= 128 or not password.strip():
            raise ValueError("Пароль: 8–128 символов, не только пробелы.")
        return password

    @staticmethod
    def validate_name(name: str) -> str:
        """Проверить имя пользователя."""
        return UserService._validate_text("Имя", name, 50)

    @staticmethod
    def validate_city(city: str) -> str:
        """Проверить название города."""
        return UserService._validate_text("Город", city, 80)

    @staticmethod
    def validate_contact(contact: str) -> str:
        """Проверить контакт для связи."""
        return UserService._validate_text("Контакт", contact, 100)

    def login(self, login: str, password: str) -> User:
        """Начать сессию при верных данных; ошибочный вход оставляет гостя."""
        self._current_user = None
        user = self._user_repository.find_by_login(login.strip())
        if user is None or not self._password_hasher.verify(
            password, user.password_hash, user.salt
        ):
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

    @staticmethod
    def _validate_text(label: str, value: str, limit: int) -> str:
        """Проверить непустое поле и убрать пробелы по краям."""
        value = value.strip()
        if not 1 <= len(value) <= limit:
            raise ValueError(f"{label}: от 1 до {limit} символов, не только пробелы.")
        return value
