from dataclasses import dataclass

from book_models import Book, BookStatus
from book_repository import BookRepository
from repositories import UserRepository


@dataclass(frozen=True)
class BookCard:
    """Публичная карточка без контакта и данных авторизации владельца."""

    book: Book
    owner_name: str
    city: str


class CatalogService:
    """Просматривать доступные книги и искать их без авторизации."""

    def __init__(self, books: BookRepository, users: UserRepository) -> None:
        """Получить хранилища для поиска книг и публичных данных владельца."""
        self._books = books
        self._users = users

    def _card(self, book: Book) -> BookCard:
        """Добавить к книге только имя и город владельца."""
        owner = self._users.find_by_login(book.owner_login)
        if owner is None:
            raise ValueError("Владелец книги не найден.")
        return BookCard(book, owner.name, owner.city)

    def search(self, query: str = "", genre: str = "", city: str = "") -> list[BookCard]:
        """Искать часть названия или автора, совместно применяя фильтры."""
        query, genre, city = (
            query.strip().casefold(),
            genre.strip().casefold(),
            city.strip().casefold(),
        )
        result = []
        for book in self._books.all():
            if book.deleted or book.status != BookStatus.AVAILABLE:
                continue
            if query and query not in book.title.casefold() and query not in book.author.casefold():
                continue
            if genre and genre != book.genre.casefold():
                continue
            card = self._card(book)
            if city and city != card.city.casefold():
                continue
            result.append(card)
        return result

    def get_card(self, book_id: int) -> BookCard:
        """Открыть доступную книгу; скрытые и занятые книги не публикуются."""
        book = self._books.get(book_id)
        if book.deleted or book.status != BookStatus.AVAILABLE:
            raise ValueError("Книга недоступна в каталоге.")
        return self._card(book)
