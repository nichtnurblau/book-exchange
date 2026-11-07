import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from src.book_cli import BookConsole
from src.cli import ConsoleApp
from src.exchange_cli import ExchangeConsole
from src.repositories.book import InMemoryBookRepository
from src.repositories.exchange import InMemoryExchangeRepository
from src.repositories.user import InMemoryUserRepository
from src.security import PasswordHasher
from src.services.book import BookService
from src.services.catalog import CatalogService
from src.services.exchange import ExchangeService
from src.services.user import UserService


class CliTests(unittest.TestCase):
    """Проверить консольный сценарий регистрации, входа и выхода."""

    def make_app(
        self, user_service: UserService, user_repository: InMemoryUserRepository
    ) -> ConsoleApp:
        """Подключить консольные разделы к тестовой сессии."""
        book_repository = InMemoryBookRepository()
        exchange_repository = InMemoryExchangeRepository()
        return ConsoleApp(
            user_service,
            BookConsole(
                BookService(user_service, book_repository, exchange_repository),
                CatalogService(book_repository, user_repository),
            ),
            ExchangeConsole(
                ExchangeService(user_service, book_repository, exchange_repository, user_repository)
            ),
        )

    def test_full_scenario(self) -> None:
        """Ошибочный ввод и выход не должны обходить проверку авторизации."""
        user_repository = InMemoryUserRepository()
        user_service = UserService(user_repository, PasswordHasher())
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
            patch("src.cli.getpass", side_effect=["testpass123", "wrong", "testpass123"]),
            redirect_stdout(output),
        ):
            self.make_app(user_service, user_repository).run()
        text = output.getvalue()
        self.assertIn("Учётная запись Reader создана", text)
        self.assertIn("Неверный логин или пароль", text)
        self.assertIn("Вход выполнен: Читатель", text)
        self.assertEqual(text.count("Сначала войдите"), 2)
        self.assertNotIn("testpass123", text)
        self.assertNotIn("reader@example.test", text)
        self.assertIsNone(user_service.current_user)

    def test_registration_checks_each_field_before_next_prompt(self) -> None:
        """Ошибка повторяет текущее поле; следующие поля ещё не запрашиваются."""
        repository = InMemoryUserRepository()
        service = UserService(repository, PasswordHasher())
        answers = {
            "Логин: ": iter(["ab", "Reader"]),
            "Имя: ": iter(["", "Читатель"]),
            "Город: ": iter([" ", "Волгоград"]),
            "Контакт: ": iter(["", "reader@example.test"]),
        }
        commands = iter(["1", "0"])
        output = io.StringIO()

        def read(prompt: str) -> str:
            print(prompt)
            if prompt == "Выберите действие: ":
                return next(commands)
            return next(answers[prompt])

        def read_password(prompt: str) -> str:
            print(prompt)
            return next(passwords)

        passwords = iter(["short", "testpass123"])
        with (
            patch("builtins.input", side_effect=read),
            patch("src.cli.getpass", side_effect=read_password),
            redirect_stdout(output),
        ):
            self.make_app(service, repository).run()
        text = output.getvalue()
        for error, next_prompt in [
            ("Ошибка: Логин:", "Пароль (ввод скрыт):"),
            ("Ошибка: Пароль:", "Имя: "),
            ("Ошибка: Имя:", "Город: "),
            ("Ошибка: Город:", "Контакт: "),
            ("Ошибка: Контакт:", "Учётная запись Reader создана"),
        ]:
            with self.subTest(error=error):
                self.assertLess(text.index(error), text.index(next_prompt))
        self.assertIsNotNone(repository.find_by_login("Reader"))
        self.assertEqual(text.count("Логин принят."), 1)
        self.assertEqual(text.count("Пароль принят."), 1)
        self.assertNotIn("short", text)
        self.assertNotIn("testpass123", text)

    def test_busy_login_is_rejected_before_password(self) -> None:
        """Занятый логин исправляется до перехода к паролю."""
        repository = InMemoryUserRepository()
        service = UserService(repository, PasswordHasher())
        service.register("Reader", "testpass123", "Читатель", "Волгоград", "contact")
        commands = ["1", "READER", "Other", "Другой", "Москва", "contact", "0"]

        def read_password(prompt: str) -> str:
            self.assertEqual(read.call_count, 3)
            return "testpass123"

        output = io.StringIO()
        with (
            patch("builtins.input", side_effect=commands) as read,
            patch("src.cli.getpass", side_effect=read_password),
            redirect_stdout(output),
        ):
            self.make_app(service, repository).run()
        self.assertIn("Этот логин уже занят", output.getvalue())
        self.assertIn("Учётная запись Other создана", output.getvalue())

    def test_menu_commands_depend_on_current_user(self) -> None:
        """Гость и пользователь видят доступные пункты с прежними номерами."""
        repository = InMemoryUserRepository()
        service = UserService(repository, PasswordHasher())
        service.register("Reader", "testpass123", "Читатель", "Волгоград", "contact")
        for logged_in in (False, True):
            with self.subTest(logged_in=logged_in):
                if logged_in:
                    service.login("Reader", "testpass123")
                output = io.StringIO()
                with patch("builtins.input", return_value="0"), redirect_stdout(output):
                    self.make_app(service, repository).run()
                lines = output.getvalue().splitlines()
                numbers = [
                    line.split(" — ")[0] for line in lines if " — " in line and line[0].isdigit()
                ]
                expected = [3, 4, 5, 6, 7, *range(8, 19), 0] if logged_in else [1, 2, 5, 6, 7, 0]
                self.assertEqual(numbers, [str(number) for number in expected])

    def test_interrupted_registration_does_not_save_user(self) -> None:
        """Прерванная регистрация не создаёт неполную учётную запись."""
        repository = InMemoryUserRepository()
        service = UserService(repository, PasswordHasher())
        with (
            patch("builtins.input", side_effect=["1", "Reader", EOFError]),
            patch("src.cli.getpass", return_value="testpass123"),
            redirect_stdout(io.StringIO()),
        ):
            self.make_app(service, repository).run()
        self.assertIsNone(repository.find_by_login("Reader"))

    def test_eof(self) -> None:
        """Конец ввода корректно закрывает программу."""
        user_repository = InMemoryUserRepository()
        user_service = UserService(user_repository, PasswordHasher())
        with patch("builtins.input", side_effect=EOFError), redirect_stdout(io.StringIO()):
            self.make_app(user_service, user_repository).run()
        self.assertIsNone(user_service.current_user)


if __name__ == "__main__":
    unittest.main()
