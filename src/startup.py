from alembic import command
from alembic.config import Config

from src.database.session import Database
from src.database.settings import get_database_url


def prepare_database() -> None:
    """Обновить схему Alembic перед запуском приложения."""
    command.upgrade(Config("alembic.ini"), "head")
    database = Database(get_database_url())
    try:
        database.check_schema()
    finally:
        database.close()
