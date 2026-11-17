import io
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from sqlalchemy.engine import make_url

from src.database.settings import get_database_url
from src.main import main


class DatabaseSettingsTests(unittest.TestCase):
    """Проверить выбор PostgreSQL и общие настройки подключения."""

    def test_default_database_is_postgresql(self) -> None:
        """Без настроек приложение подключается к локальному PostgreSQL."""
        with patch.dict(os.environ, {}, clear=True):
            url = make_url(get_database_url())
        self.assertEqual(url.drivername, "postgresql+psycopg")
        self.assertEqual(url.host, "localhost")
        self.assertEqual(url.port, 5432)
        self.assertEqual(url.database, "bookexchange")
        self.assertEqual(url.username, "bookexchange")

    def test_postgres_fields_and_special_password(self) -> None:
        """Порт и реквизиты берутся из окружения, знаки в пароле сохраняются."""
        settings = {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5433",
            "POSTGRES_DB": "reader_books",
            "POSTGRES_USER": "reader",
            "POSTGRES_PASSWORD": "pass@word:/?#",
        }
        with patch.dict(os.environ, settings, clear=True):
            url = make_url(get_database_url())
        self.assertEqual(url.port, 5433)
        self.assertEqual(url.database, "reader_books")
        self.assertEqual(url.username, "reader")
        self.assertEqual(url.password, settings["POSTGRES_PASSWORD"])

    def test_explicit_url_has_priority(self) -> None:
        """Готовый адрес внешней БД перекрывает отдельные POSTGRES-переменные."""
        url = "postgresql+psycopg://reader:password@db.example.test:5433/books"
        with patch.dict(os.environ, {"DATABASE_URL": url, "POSTGRES_PORT": "bad"}, clear=True):
            self.assertEqual(get_database_url(), url)

    def test_invalid_port(self) -> None:
        """Нечисловой порт и значения вне диапазона дают понятную ошибку."""
        for port in ("abc", "0", "65536"):
            with self.subTest(port=port):
                with patch.dict(os.environ, {"POSTGRES_PORT": port}, clear=True):
                    with self.assertRaisesRegex(ValueError, "POSTGRES_PORT"):
                        get_database_url()

    def test_bad_settings_are_reported_without_traceback(self) -> None:
        """Точка входа обрабатывает ошибку конфигурации до подключения к БД."""
        output = io.StringIO()
        with (
            patch.dict(os.environ, {"POSTGRES_PORT": "bad"}, clear=True),
            redirect_stdout(output),
        ):
            main()
        self.assertIn("Ошибка запуска: POSTGRES_PORT", output.getvalue())
        self.assertNotIn("Traceback", output.getvalue())
