import sys
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from book_models import GENRES, Book, BookStatus
from book_repository import InMemoryBookRepository
from catalog import CatalogService
from models import User
from repositories import InMemoryUserRepository


class CatalogTests(unittest.TestCase):
    """Проверить поиск, фильтры и публичность каталога по Ф5."""

    def setUp(self) -> None:
        """Подготовить книги разных городов и жанров без сессии пользователя."""
        users = InMemoryUserRepository()
        users.add(User("anna", "Анна", "Волгоград", "private-contact", b"", b""))
        users.add(User("boris", "Борис", "Москва", "another-private", b"", b""))
        self.books = InMemoryBookRepository()
        self.first = self.books.add(
            Book(0, "anna", "Белый клык", "Джек Лондон", GENRES[0], "Хорошее")
        )
        self.books.add(Book(0, "boris", "Белый клык", "Джек Лондон", GENRES[0], "Новое"))
        self.books.add(Book(0, "anna", "Алгебра", "Иван Петров", GENRES[1], "Новое"))
        self.catalog = CatalogService(self.books, users)

    def test_russian_partial_search(self) -> None:
        """Части названия и автора ищутся без учёта регистра."""
        self.assertEqual(len(self.catalog.search("КЛЫК")), 2)
        self.assertEqual(len(self.catalog.search("лОНД")), 2)

    def test_combined_filters(self) -> None:
        """Поисковая строка, жанр и город действуют одновременно."""
        cards = self.catalog.search("бел", GENRES[0], "волГОград")
        self.assertEqual([card.book.id for card in cards], [self.first.id])
        self.assertEqual(self.catalog.search("бел", GENRES[1], "Волгоград"), [])
        self.assertEqual(self.catalog.search("несуществующее"), [])

    def test_hidden_and_busy_books(self) -> None:
        """Зарезервированные, обмененные и удалённые книги скрыты от гостей."""
        for change in [
            dict(status=BookStatus.RESERVED),
            dict(status=BookStatus.EXCHANGED),
            dict(deleted=True),
        ]:
            with self.subTest(change=change):
                self.books.save(replace(self.first, **change))
                self.assertEqual(len(self.catalog.search()), 2)
                with self.assertRaises(ValueError):
                    self.catalog.get_card(self.first.id)

    def test_public_card_has_no_contact(self) -> None:
        """Карточка содержит имя и город без контакта или пароля."""
        card = self.catalog.get_card(self.first.id)
        self.assertEqual((card.owner_name, card.city), ("Анна", "Волгоград"))
        self.assertNotIn("private-contact", repr(card))
        self.assertFalse(hasattr(card, "contact"))
        with self.assertRaises(ValueError):
            self.catalog.get_card(999)


if __name__ == "__main__":
    unittest.main()
