import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from auth import AuthService
from models import User
from repositories import InMemoryUserRepository
from security import PasswordHasher


class AuthTests(unittest.TestCase):
    """Проверки требований Ф1 и Ф2 без сторонних библиотек."""

    def setUp(self) -> None:
        """Создать отдельные сервис и хранилище для каждой проверки."""
        self.repository = InMemoryUserRepository()
        self.auth = AuthService(self.repository, PasswordHasher())

    def register(self, **changes: str) -> User:
        """Создать тестовую запись с возможной заменой полей."""
        fields = dict(
            login="Reader_1",
            password="testpass123",
            name="Читатель",
            city="Волгоград",
            contact="reader@example.test",
        )
        fields.update(changes)
        return self.auth.register(**fields)

    def test_registration_does_not_log_in(self) -> None:
        """Регистрация сохраняет данные, но не создаёт сессию."""
        user = self.register()
        self.assertEqual(user.city, "Волгоград")
        self.assertIs(self.repository.find_by_login("reader_1"), user)
        self.assertIsNone(self.auth.current_user)

    def test_duplicate_login_case_insensitive(self) -> None:
        """Различие регистра не позволяет занять тот же логин."""
        original = self.register()
        with self.assertRaises(ValueError):
            self.register(login="READER_1")
        self.assertIs(self.repository.find_by_login("reader_1"), original)

    def test_invalid_fields_are_not_saved(self) -> None:
        """Неверные поля не создают неполных записей."""
        for field, value in [
            ("login", "ab"),
            ("login", "ярус"),
            ("login", "a" * 31),
            ("password", "short"),
            ("password", " " * 8),
            ("password", "a" * 129),
            ("name", "  "),
            ("name", "a" * 51),
            ("city", ""),
            ("city", "a" * 81),
            ("contact", " "),
            ("contact", "a" * 101),
        ]:
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValueError):
                    self.register(**{field: value})
                self.assertIsNone(self.repository.find_by_login("Reader_1"))

    def test_valid_boundaries(self) -> None:
        """Минимальные и максимальные длины принимаются."""
        self.register(login="abc", password="x" * 8, name="Я", city="А", contact="Б")
        self.register(
            login="a" * 30, password="x" * 128, name="Я" * 50, city="А" * 80, contact="Б" * 100
        )

    def test_password_hash_and_salt(self) -> None:
        """Одинаковые пароли получают разные соли и хеши."""
        first = self.register()
        second = self.register(login="Reader_2")
        self.assertNotEqual(first.salt, second.salt)
        self.assertNotEqual(first.password_hash, second.password_hash)
        self.assertNotIn("testpass123", repr(first))

    def test_login_and_logout(self) -> None:
        """Выход закрывает доступ, а запись остаётся до завершения программы."""
        user = self.register()
        self.assertIs(self.auth.login("READER_1", "testpass123"), user)
        self.assertIs(self.auth.require_user(), user)
        self.auth.logout()
        with self.assertRaises(PermissionError):
            self.auth.require_user()
        self.assertIs(self.auth.login("reader_1", "testpass123"), user)

    def test_wrong_credentials_clear_session(self) -> None:
        """Неверные данные не оставляют активную сессию."""
        self.register()
        for login, password in [("Reader_1", "wrong"), ("unknown", "testpass123")]:
            self.auth.login("Reader_1", "testpass123")
            with self.assertRaises(ValueError):
                self.auth.login(login, password)
            self.assertIsNone(self.auth.current_user)

    def test_password_spaces_are_significant(self) -> None:
        """Пароль не обрезается при регистрации и входе."""
        self.register(password=" testpass123 ")
        with self.assertRaises(ValueError):
            self.auth.login("Reader_1", "testpass123")
        self.auth.login("Reader_1", " testpass123 ")

    def test_new_storage_is_empty(self) -> None:
        """Новый экземпляр хранилища не наследует данные старого."""
        self.register()
        self.assertIsNone(InMemoryUserRepository().find_by_login("Reader_1"))


if __name__ == "__main__":
    unittest.main()
