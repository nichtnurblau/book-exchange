import os
import unittest
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url

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

    @staticmethod
    def drop_schema(engine: Engine, schema: str) -> None:
        """Удалить только временную схему после закрытия тестовой сессии."""
        with engine.connect() as connection:
            connection.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
