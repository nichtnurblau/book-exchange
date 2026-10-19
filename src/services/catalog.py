from src.book_models import Book, BookStatus
from src.catalog import BookCard, Catalog
from src.repositories.book import BookRepository
from src.repositories.user import UserRepository


class CatalogService:
    """Собирать актуальный каталог из хранилищ и выполнять запросы к нему."""

    def __init__(self, books: BookRepository, users: UserRepository) -> None:
        """Получить хранилища книг и данных владельцев."""
        self._books = books
        self._users = users

    def search(self, query: str = "", genre: str = "", city: str = "") -> list[BookCard]:
        """Создать свежий снимок каталога и применить условия поиска."""
        return self._build_catalog().search(query, genre, city)

    def get_card(self, book_id: int) -> BookCard:
        """Проверить доступность объявления и получить его публичную карточку."""
        book = self._books.get(book_id)
        if book.deleted or book.status != BookStatus.AVAILABLE:
            raise ValueError("Книга недоступна в каталоге.")
        return Catalog((self._card(book),)).get_card(book_id)

    def _build_catalog(self) -> Catalog:
        """Собрать снимок только из актуальных доступных объявлений."""
        return Catalog(
            tuple(
                self._card(book)
                for book in self._books.all()
                if not book.deleted and book.status == BookStatus.AVAILABLE
            )
        )

    def _card(self, book: Book) -> BookCard:
        """Добавить имя и город владельца без раскрытия контакта."""
        owner = self._users.find_by_login(book.owner_login)
        if owner is None:
            raise ValueError("Владелец книги не найден.")
        return BookCard(book, owner.name, owner.city)
