from sqlalchemy.orm import Session

from src.repositories.book import SQLAlchemyBookRepository
from src.repositories.exchange import SQLAlchemyExchangeRepository
from src.repositories.user import SQLAlchemyUserRepository
from src.security import PasswordHasher
from src.services.book import BookService
from src.services.catalog import CatalogService
from src.services.exchange import ExchangeService
from src.services.user import UserService


class ServiceFactory:
    """Сервисы одного HTTP-запроса с общей Session как Unit of Work."""

    def __init__(self, session: Session) -> None:
        """Создать адаптеры хранилищ и передать их сервисному слою."""
        user_repository = SQLAlchemyUserRepository(session, commit_on_add=False)
        book_repository = SQLAlchemyBookRepository(session, commit_on_add=False)
        exchange_repository = SQLAlchemyExchangeRepository(session)
        self.user_service = UserService(user_repository, PasswordHasher())
        self.book_service = BookService(self.user_service, book_repository, exchange_repository)
        self.catalog_service = CatalogService(book_repository, user_repository)
        self.exchange_service = ExchangeService(
            self.user_service, book_repository, exchange_repository, user_repository
        )
