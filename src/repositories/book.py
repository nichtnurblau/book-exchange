from abc import ABC, abstractmethod
from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.mappers import BookMapper
from src.database.models import BookRecord
from src.models.book import Book


class BookRepository(ABC):
    """Договор хранения объявлений, включая скрытые записи для истории."""

    @abstractmethod
    def add(self, book: Book) -> Book:
        """Выдать уникальный ID и сохранить новую запись."""
        ...

    @abstractmethod
    def get(self, book_id: int) -> Book:
        """Найти запись по ID; при отсутствии вызвать ValueError."""
        ...

    @abstractmethod
    def all(self) -> list[Book]:
        """Вернуть записи, включая скрытые."""
        ...

    @abstractmethod
    def save(self, book: Book) -> None:
        """Заменить существующую запись по её ID."""
        ...


class InMemoryBookRepository(BookRepository):
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


class SQLAlchemyBookRepository(BookRepository):
    """Хранить книги в БД, возвращая предметные объекты через маппер."""

    def __init__(self, session: Session, commit_on_add: bool = True) -> None:
        """Получить сессию базы данных."""
        self._session = session
        self._commit_on_add = commit_on_add

    def add(self, book: Book) -> Book:
        """Сохранить новую книгу и получить ID от базы данных."""
        record = BookMapper.to_record(book)
        self._session.add(record)
        if self._commit_on_add:
            self._session.commit()
        else:
            self._session.flush()
        self._session.refresh(record)
        return BookMapper.to_domain(record)

    def get(self, book_id: int) -> Book:
        """Найти книгу, включая скрытую запись для истории."""
        record = self._session.get(BookRecord, book_id)
        if record is None:
            raise ValueError("Книга с таким ID не найдена.")
        return BookMapper.to_domain(record)

    def all(self) -> list[Book]:
        """Вернуть книги в стабильном порядке ID."""
        return [
            BookMapper.to_domain(record)
            for record in self._session.scalars(select(BookRecord).order_by(BookRecord.id))
        ]

    def save(self, book: Book) -> None:
        """Обновить существующую книгу, сохранив прежний ID."""
        record = self._session.get(BookRecord, book.id)
        if record is None:
            raise ValueError("Книга с таким ID не найдена.")
        BookMapper.update_record(book, record)
        self._session.flush()
