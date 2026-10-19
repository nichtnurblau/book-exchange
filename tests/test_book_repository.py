import unittest
from dataclasses import FrozenInstanceError, replace

from src.book_models import GENRES, Book
from src.repositories.book import InMemoryBookRepository


class BookRepositoryTests(unittest.TestCase):
    """Проверить идентификаторы и сохранение скрытых книг для истории."""

    def test_ids_history_and_immutable_records(self) -> None:
        """Удаление не освобождает ID и не уничтожает запись."""
        repo = InMemoryBookRepository()
        first = repo.add(Book(0, "reader", "Книга", "Автор", GENRES[0], "Новое"))
        repo.save(replace(first, deleted=True))
        second = repo.add(first)
        self.assertNotEqual(first.id, second.id)
        self.assertTrue(repo.get(first.id).deleted)
        snapshot = repo.all()
        snapshot.clear()
        self.assertEqual(len(repo.all()), 2)
        with self.assertRaises(FrozenInstanceError):
            first.title = "Подмена"
        with self.assertRaises(ValueError):
            repo.get(999)
        self.assertEqual(InMemoryBookRepository().all(), [])


if __name__ == "__main__":
    unittest.main()
