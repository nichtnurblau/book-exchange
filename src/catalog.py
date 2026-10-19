from dataclasses import dataclass

from src.book_models import Book, BookStatus


@dataclass(frozen=True)
class BookCard:
    """Публичная карточка без контакта и данных авторизации владельца."""

    book: Book
    owner_name: str
    city: str


@dataclass(frozen=True)
class Catalog:
    """Снимок карточек с правилами отбора доступных объявлений."""

    cards: tuple[BookCard, ...]

    def search(self, query: str = "", genre: str = "", city: str = "") -> list[BookCard]:
        """Искать часть названия или автора с совместными фильтрами."""
        query, genre, city = (
            query.strip().casefold(),
            genre.strip().casefold(),
            city.strip().casefold(),
        )
        result = []
        for card in self.cards:
            book = card.book
            if book.deleted or book.status != BookStatus.AVAILABLE:
                continue
            if query and query not in book.title.casefold() and query not in book.author.casefold():
                continue
            if genre and genre != book.genre.casefold():
                continue
            if city and city != card.city.casefold():
                continue
            result.append(card)
        return result

    def get_card(self, book_id: int) -> BookCard:
        """Открыть доступную карточку; скрытые и занятые книги недоступны."""
        for card in self.cards:
            if card.book.id == book_id:
                if card.book.deleted or card.book.status != BookStatus.AVAILABLE:
                    raise ValueError("Книга недоступна в каталоге.")
                return card
        raise ValueError("Книга с таким ID не найдена.")
