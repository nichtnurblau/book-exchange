import tempfile
from pathlib import Path

from src.database.repositories.book import SQLAlchemyBookRepository
from src.database.repositories.exchange import SQLAlchemyExchangeRepository
from src.database.repositories.user import SQLAlchemyUserRepository
from src.database.session import Database
from src.services.book import BookService
from src.services.catalog import CatalogService
from src.services.exchange import ExchangeService
from src.services.user import UserService
from tests import test_exchange_flow
from tests.db_support import migrate


class SQLExchangeFlowTests(test_exchange_flow.ExchangeFlowTests):
    """Повторить все правила Ф3–Ф10 на настоящих SQL-репозиториях."""

    def setUp(self) -> None:
        """Создать схему миграцией и перенести исходные записи в SQL."""
        super().setUp()
        initial_users = [
            self.user_repository.find_by_login(login) for login in ("anna", "boris", "vera")
        ]
        initial_books = self.book_repository.all()
        self.folder = tempfile.TemporaryDirectory()
        url = "sqlite:///" + str(Path(self.folder.name) / "test.db")
        migrate(url)
        self.database = Database(url)
        self.context = self.database.transaction()
        self.context.__enter__()
        self.addCleanup(self.folder.cleanup)
        self.addCleanup(self.database.close)
        self.addCleanup(self.context.__exit__, None, None, None)
        self.user_repository = SQLAlchemyUserRepository(self.database.session)
        self.book_repository = SQLAlchemyBookRepository(self.database.session)
        self.exchange_repository = SQLAlchemyExchangeRepository(self.database.session)
        for user in initial_users:
            self.user_repository.add(user)
        for book in initial_books:
            self.book_repository.add(book)
        self.user_service = UserService(self.user_repository, self.hasher)
        self.service = BookService(
            self.user_service, self.book_repository, self.exchange_repository
        )
        self.exchange = ExchangeService(
            self.user_service, self.book_repository, self.exchange_repository, self.user_repository
        )
        self.catalog = CatalogService(self.book_repository, self.user_repository)
        self.login("anna")
