from src.book_cli import BookConsole
from src.cli import ConsoleApp
from src.exchange_cli import ExchangeConsole
from src.repositories.book import InMemoryBookRepository
from src.repositories.exchange import InMemoryExchangeRepository
from src.repositories.user import InMemoryUserRepository
from src.security import PasswordHasher
from src.services.book import BookService
from src.services.catalog import CatalogService
from src.services.exchange import ExchangeService
from src.services.user import UserService


def main() -> None:
    """Собрать хранилища, сервисы и интерфейс и запустить программу."""
    user_repository = InMemoryUserRepository()
    book_repository = InMemoryBookRepository()
    exchange_repository = InMemoryExchangeRepository()
    user_service = UserService(user_repository, PasswordHasher())
    book_cli = BookConsole(
        BookService(user_service, book_repository, exchange_repository),
        CatalogService(book_repository, user_repository),
    )
    exchange_cli = ExchangeConsole(
        ExchangeService(user_service, book_repository, exchange_repository, user_repository)
    )
    ConsoleApp(user_service, book_cli, exchange_cli).run()


if __name__ == "__main__":
    main()
