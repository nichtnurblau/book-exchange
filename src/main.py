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
    users = InMemoryUserRepository()
    books = InMemoryBookRepository()
    exchanges = InMemoryExchangeRepository()
    auth = UserService(users, PasswordHasher())
    book_console = BookConsole(BookService(auth, books, exchanges), CatalogService(books, users))
    exchange_console = ExchangeConsole(ExchangeService(auth, books, exchanges, users))
    ConsoleApp(auth, book_console, exchange_console).run()


if __name__ == "__main__":
    main()
