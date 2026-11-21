from src.cli.app import ConsoleApp
from src.cli.book import BookConsole
from src.cli.exchange import ExchangeConsole
from src.database.session import Database
from src.database.settings import get_database_url
from src.repositories.book import SQLAlchemyBookRepository
from src.repositories.exchange import SQLAlchemyExchangeRepository
from src.repositories.user import SQLAlchemyUserRepository
from src.security import PasswordHasher
from src.services.book import BookService
from src.services.catalog import CatalogService
from src.services.exchange import ExchangeService
from src.services.user import UserService


def run_cli() -> None:
    """Подключить SQL-репозитории к сервисам и запустить консоль."""
    database: Database | None = None
    try:
        database = Database(get_database_url())
        database.check_schema()
        user_repository = SQLAlchemyUserRepository(database.session)
        book_repository = SQLAlchemyBookRepository(database.session)
        exchange_repository = SQLAlchemyExchangeRepository(database.session)
        user_service = UserService(user_repository, PasswordHasher())
        book_cli = BookConsole(
            BookService(user_service, book_repository, exchange_repository),
            CatalogService(book_repository, user_repository),
        )
        exchange_cli = ExchangeConsole(
            ExchangeService(user_service, book_repository, exchange_repository, user_repository)
        )
        ConsoleApp(
            user_service, book_cli, exchange_cli, database.transaction, persistent=True
        ).run()
    except ValueError as error:
        print(f"Ошибка запуска: {error}")
    finally:
        if database is not None:
            database.close()


if __name__ == "__main__":
    run_cli()
