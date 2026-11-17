import os

from sqlalchemy.engine import URL


def get_database_url() -> str:
    """Получить адрес PostgreSQL из настроек или использовать явный DATABASE_URL."""
    if url := os.environ.get("DATABASE_URL"):
        return url
    try:
        port = int(os.environ.get("POSTGRES_PORT", "5432"))
    except ValueError:
        raise ValueError("POSTGRES_PORT должен быть целым числом от 1 до 65535.") from None
    if not 1 <= port <= 65535:
        raise ValueError("POSTGRES_PORT должен быть целым числом от 1 до 65535.")
    return URL.create(
        "postgresql+psycopg",
        username=os.environ.get("POSTGRES_USER", "bookexchange"),
        password=os.environ.get("POSTGRES_PASSWORD", "bookexchange"),
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=port,
        database=os.environ.get("POSTGRES_DB", "bookexchange"),
    ).render_as_string(hide_password=False)
