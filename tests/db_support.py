import os
from pathlib import Path
from unittest.mock import patch

from alembic import command
from alembic.config import Config

ROOT = Path(__file__).resolve().parents[1]


def migration_config() -> Config:
    """Подготовить Alembic с абсолютными путями и без перенастройки логов."""
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    config.attributes["configure_logger"] = False
    return config


def migrate(url: str, revision: str = "head") -> None:
    """Создать тестовую схему только через настоящие миграции."""
    with patch.dict(os.environ, {"DATABASE_URL": url}):
        command.upgrade(migration_config(), revision)
