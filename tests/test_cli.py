import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from auth import AuthService
from cli import ConsoleApp
from repositories import InMemoryUserRepository
from security import PasswordHasher


class CliTests(unittest.TestCase):
    """Проверить консольный сценарий регистрации, входа и выхода."""

    def test_full_scenario(self) -> None:
        """Ошибочный ввод и выход не должны обходить проверку авторизации."""
        auth = AuthService(InMemoryUserRepository(), PasswordHasher())
        commands = [
            "9",
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
            ConsoleApp(auth).run()
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
        auth = AuthService(InMemoryUserRepository(), PasswordHasher())
        with patch("builtins.input", side_effect=EOFError), redirect_stdout(io.StringIO()):
            ConsoleApp(auth).run()
        self.assertIsNone(auth.current_user)


if __name__ == "__main__":
    unittest.main()
