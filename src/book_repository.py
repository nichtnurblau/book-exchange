from dataclasses import replace
from typing import Protocol

from book_models import Book


class BookRepository(Protocol):
    """Договор хранения объявлений, включая скрытые записи для истории."""

    def add(self, book: Book) -> Book:
        """Выдать уникальный ID и сохранить новую запись."""
        ...

    def get(self, book_id: int) -> Book:
        """Найти запись по ID; при отсутствии вызвать ValueError."""
        ...

    def all(self) -> list[Book]:
        """Вернуть записи, включая скрытые."""
        ...

    def save(self, book: Book) -> None:
        """Заменить существующую запись по её ID."""
        ...


class InMemoryBookRepository:
    """Хранить объявления в словаре на время одного запуска."""

    def __init__(self) -> None:
        """Создать словарь и счётчик идентификаторов."""
        self._books: dict[int, Book] = {}
        self._next_id = 1

    def add(self, book: Book) -> Book:
        """Создать запись с очередным идентификатором."""
        saved = replace(book, id=self._next_id)
        self._books[saved.id] = saved
        self._next_id += 1
        return saved

    def get(self, book_id: int) -> Book:
        """Найти запись либо сообщить об ошибочном ID."""
        if book_id not in self._books:
            raise ValueError("Книга с таким ID не найдена.")
        return self._books[book_id]

    def all(self) -> list[Book]:
        """Вернуть новый список неизменяемых записей."""
        return list(self._books.values())

    def save(self, book: Book) -> None:
        """Заменить только ранее созданную запись."""
        self.get(book.id)
        self._books[book.id] = book
