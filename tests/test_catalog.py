import unittest
from dataclasses import replace

from src.book_models import GENRES, Book, BookStatus
from src.catalog import BookCard, Catalog
from src.models import User
from src.repositories.book import InMemoryBookRepository
from src.repositories.user import InMemoryUserRepository
from src.services.catalog import CatalogService


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

    def test_catalog_is_an_independent_snapshot(self) -> None:
        """Каталог ищет карточки без доступа к сервису или хранилищу."""
        available = BookCard(self.first, "Анна", "Волгоград")
        reserved = BookCard(
            replace(self.first, id=100, status=BookStatus.RESERVED), "Анна", "Волгоград"
        )
        catalog = Catalog((available, reserved))
        self.assertEqual(catalog.search("КЛЫК", GENRES[0], "волгоград"), [available])
        self.assertEqual(catalog.get_card(self.first.id), available)
        with self.assertRaises(ValueError):
            catalog.get_card(100)
        with self.assertRaises(ValueError):
            catalog.get_card(999)

    def test_service_refreshes_catalog_after_changes(self) -> None:
        """Сервис не оставляет в выдаче книгу из устаревшего снимка."""
        snapshot = self.catalog.search()
        self.books.save(replace(self.first, status=BookStatus.RESERVED))
        self.assertEqual(len(snapshot), 3)
        self.assertEqual(len(self.catalog.search()), 2)
        with self.assertRaises(ValueError):
            self.catalog.get_card(self.first.id)


if __name__ == "__main__":
    unittest.main()
