from src.book_cli import BookConsole
from src.cli import ConsoleApp
from src.database.repositories.book import SQLAlchemyBookRepository
from src.database.repositories.exchange import SQLAlchemyExchangeRepository
from src.database.repositories.user import SQLAlchemyUserRepository
from src.database.session import Database
from src.database.settings import get_database_url
from src.exchange_cli import ExchangeConsole
from src.security import PasswordHasher
from src.services.book import BookService
from src.services.catalog import CatalogService
from src.services.exchange import ExchangeService
from src.services.user import UserService


def main() -> None:
    """Подключить SQL-репозитории к сервисам и запустить консоль."""
    database = Database(get_database_url())
    try:
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
        database.close()


if __name__ == "__main__":
    main()
