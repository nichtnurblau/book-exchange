from sqlalchemy import select
from sqlalchemy.orm import Session

from src.book_models import Book
from src.database.mappers import BookMapper
from src.database.models import BookRecord
from src.repositories.book import BookRepository


class SQLAlchemyBookRepository(BookRepository):
    """Хранить книги в БД, возвращая предметные объекты через маппер."""

    def __init__(self, session: Session) -> None:
        """Получить сессию базы данных."""
        self._session = session

    def add(self, book: Book) -> Book:
        """Сохранить новую книгу и получить ID от базы данных."""
        record = BookMapper.to_record(book)
        self._session.add(record)
        self._session.commit()
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
