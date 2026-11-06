from collections.abc import Iterator
from contextlib import contextmanager
from sqlite3 import Connection

from sqlalchemy import create_engine, event
from sqlalchemy.exc import DBAPIError, IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.pool import ConnectionPoolEntry


class Database:
    """Владеть подключением и транзакцией одной команды приложения."""

    def __init__(self, url: str) -> None:
        """Создать движок и сессию, не создавая таблицы."""
        options = {"isolation_level": "SERIALIZABLE"} if url.startswith("postgresql") else {}
        self.engine = create_engine(url, **options)
        if self.engine.dialect.name == "sqlite":
            event.listen(self.engine, "connect", self._sqlite_foreign_keys)
        self.session = Session(self.engine)

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Сохранить команду целиком или откатить все её изменения."""
        try:
            with self.session.begin():
                yield
        except IntegrityError:
            raise ValueError("Операция нарушает ограничения БД. Изменения не сохранены.") from None
        except DBAPIError:
            raise ValueError(
                "Не удалось выполнить операцию с БД. Изменения отменены; повторите команду."
            ) from None

    def check_schema(self) -> None:
        """Проверить наличие актуальной схемы перед запуском меню."""
        from alembic.config import Config
        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory

        try:
            with self.engine.connect() as connection:
                heads = MigrationContext.configure(connection).get_current_heads()
            expected = ScriptDirectory.from_config(Config("alembic.ini")).get_heads()
            if set(heads) != set(expected):
                raise ValueError("Схема БД не обновлена. Выполните: uv run alembic upgrade head")
        except SQLAlchemyError:
            raise ValueError("БД недоступна. Проверьте DATABASE_URL и запуск PostgreSQL.") from None

    def close(self) -> None:
        """Закрыть сессию и пул подключений."""
        self.session.close()
        self.engine.dispose()

    @staticmethod
    def _sqlite_foreign_keys(
        connection: Connection, connection_record: ConnectionPoolEntry
    ) -> None:
        """Включить контроль внешних ключей для каждого SQLite-подключения."""
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
