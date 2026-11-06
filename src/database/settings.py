import os


def get_database_url() -> str:
    """Получить адрес БД; без настройки использовать локальный файл SQLite."""
    return os.environ.get("DATABASE_URL", "sqlite:///book_exchange.db")
