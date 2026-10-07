import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from auth import AuthService
from book_cli import BookConsole
from book_repository import InMemoryBookRepository
from books import BookService
from catalog import CatalogService
from cli import ConsoleApp
from exchange_cli import ExchangeConsole
from exchange_repository import InMemoryExchangeRepository
from exchanges import ExchangeService
from repositories import InMemoryUserRepository
from security import PasswordHasher


class CliTests(unittest.TestCase):
    """Проверить консольный сценарий регистрации, входа и выхода."""

    def make_app(self, auth: AuthService, users: InMemoryUserRepository) -> ConsoleApp:
        """Подключить консольные разделы к тестовой сессии."""
        books = InMemoryBookRepository()
        exchanges = InMemoryExchangeRepository()
        return ConsoleApp(
            auth,
            BookConsole(BookService(auth, books, exchanges), CatalogService(books, users)),
            ExchangeConsole(ExchangeService(auth, books, exchanges, users)),
        )

    def test_full_scenario(self) -> None:
        """Ошибочный ввод и выход не должны обходить проверку авторизации."""
        users = InMemoryUserRepository()
        auth = AuthService(users, PasswordHasher())
        commands = [
            "99",
            "3",
            "1",
            "Reader",
            "Читатель",
            "Волгоград",
            "reader@example.test",
            "2",
            "Reader",
            "2",
            "READER",
            "3",
            "4",
            "3",
            "0",
        ]
        output = io.StringIO()
        with (
            patch("builtins.input", side_effect=commands),
            patch("cli.getpass", side_effect=["testpass123", "wrong", "testpass123"]),
            redirect_stdout(output),
        ):
            self.make_app(auth, users).run()
        text = output.getvalue()
        self.assertIn("Учётная запись Reader создана", text)
        self.assertIn("Неверный логин или пароль", text)
        self.assertIn("Вход выполнен: Читатель", text)
        self.assertEqual(text.count("Сначала войдите"), 2)
        self.assertNotIn("testpass123", text)
        self.assertNotIn("reader@example.test", text)
        self.assertIsNone(auth.current_user)

    def test_eof(self) -> None:
        """Конец ввода корректно закрывает программу."""
        users = InMemoryUserRepository()
        auth = AuthService(users, PasswordHasher())
        with patch("builtins.input", side_effect=EOFError), redirect_stdout(io.StringIO()):
            self.make_app(auth, users).run()
        self.assertIsNone(auth.current_user)


if __name__ == "__main__":
    unittest.main()
