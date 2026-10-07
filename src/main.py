from auth import AuthService
from book_cli import BookConsole
from book_repository import InMemoryBookRepository
from books import BookService
from catalog import CatalogService
from cli import ConsoleApp
from exchange_cli import ExchangeConsole
from exchange_repository import InMemoryExchangeRepository
from exchanges import ExchangeService
from repositories import InMemoryUserRepository
from security import PasswordHasher


def main() -> None:
    """Собрать хранилища, сервисы и интерфейс и запустить программу."""
    users = InMemoryUserRepository()
    books = InMemoryBookRepository()
    exchanges = InMemoryExchangeRepository()
    auth = AuthService(users, PasswordHasher())
    book_console = BookConsole(BookService(auth, books, exchanges), CatalogService(books, users))
    exchange_console = ExchangeConsole(ExchangeService(auth, books, exchanges, users))
    ConsoleApp(auth, book_console, exchange_console).run()


if __name__ == "__main__":
    main()
