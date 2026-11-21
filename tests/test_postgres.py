import io
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url

from src.cli.runner import run_cli as main
from tests import test_database


@unittest.skipUnless(os.environ.get("TEST_POSTGRES_URL"), "Не задан TEST_POSTGRES_URL")
class PostgreSQLDatabaseTests(test_database.DatabaseTests):
    """Повторить проверки БД на PostgreSQL в отдельных временных схемах."""

    def make_database_url(self) -> str:
        """Создать изолированную схему, не изменяя таблицы приложения."""
        url = make_url(os.environ["TEST_POSTGRES_URL"])
        if url.get_backend_name() != "postgresql":
            raise ValueError("TEST_POSTGRES_URL должен указывать на PostgreSQL.")
        schema = "test_" + uuid4().hex
        engine = create_engine(url, isolation_level="AUTOCOMMIT")
        self.addCleanup(engine.dispose)
        with engine.connect() as connection:
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
        self.addCleanup(self.drop_schema, engine, schema)
        return url.update_query_dict({"options": "-csearch_path=" + schema}).render_as_string(
            hide_password=False
        )

    def test_console_registration_survives_restart(self) -> None:
        """Созданная через консоль учётная запись доступна после нового запуска."""
        commands = [
            "1",
            "PgReader",
            "Читатель",
            "Волгоград",
            "reader@example.test",
            "0",
            "2",
            "PgReader",
            "0",
        ]
        output = io.StringIO()
        with (
            patch("src.cli.runner.get_database_url", return_value=self.url),
            patch("builtins.input", side_effect=commands),
            patch("src.cli.app.getpass", side_effect=["testpass123", "testpass123"]),
            redirect_stdout(output),
        ):
            main()
            main()
        text = output.getvalue()
        self.assertIn("Учётная запись PgReader создана", text)
        self.assertIn("Вход выполнен: Читатель", text)
        self.assertNotIn("Ошибка запуска", text)
        self.assertNotIn("testpass123", text)

    @staticmethod
    def drop_schema(engine: Engine, schema: str) -> None:
        """Удалить только временную схему после закрытия тестовой сессии."""
        with engine.connect() as connection:
            connection.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
