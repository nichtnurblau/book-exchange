from datetime import timezone

from src.book_models import Book, BookStatus
from src.database.models import BookRecord, ExchangeRecord, UserRecord
from src.exchange_models import Exchange, ExchangeStatus
from src.models import User


class UserMapper:
    """Преобразовывать учётную запись между dataclass и ORM."""

    @staticmethod
    def to_domain(record: UserRecord) -> User:
        """Вернуть независимый от сессии объект пользователя."""
        return User(
            record.display_login,
            record.name,
            record.city,
            record.contact,
            record.password_hash,
            record.salt,
        )

    @staticmethod
    def to_record(user: User) -> UserRecord:
        """Нормализовать ключ, сохранив исходный логин для отображения."""
        return UserRecord(
            login=user.login.casefold(),
            display_login=user.login,
            name=user.name,
            city=user.city,
            contact=user.contact,
            password_hash=user.password_hash,
            salt=user.salt,
        )


class BookMapper:
    """Преобразовывать объявления между предметной моделью и таблицей."""

    @staticmethod
    def to_domain(record: BookRecord) -> Book:
        """Получить неизменяемую книгу с исходным логином владельца."""
        return Book(
            record.id,
            record.owner.display_login,
            record.title,
            record.author,
            record.genre,
            record.condition,
            record.description,
            BookStatus(record.status),
            record.deleted,
        )

    @staticmethod
    def update_record(book: Book, record: BookRecord) -> None:
        """Перенести поля, не меняя выданный базой идентификатор."""
        record.owner_login = book.owner_login.casefold()
        record.title, record.author, record.genre = book.title, book.author, book.genre
        record.condition, record.description = book.condition, book.description
        record.status, record.deleted = book.status.value, book.deleted

    @staticmethod
    def to_record(book: Book) -> BookRecord:
        """Подготовить новую запись; ID будет выдан БД при flush."""
        record = BookRecord()
        BookMapper.update_record(book, record)
        return record


class ExchangeMapper:
    """Преобразовывать заявки и подтверждения между dataclass и ORM."""

    @staticmethod
    def to_domain(record: ExchangeRecord) -> Exchange:
        """Вернуть заявку, восстановив UTC при чтении SQLite."""
        date = record.created_at
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        return Exchange(
            record.id,
            record.requested_id,
            record.offered_id,
            record.sender.display_login,
            record.recipient.display_login,
            date,
            ExchangeStatus(record.status),
            frozenset(user.display_login for user in record.confirmed_by),
        )

    @staticmethod
    def update_record(
        exchange: Exchange, record: ExchangeRecord, confirmations: list[UserRecord]
    ) -> None:
        """Перенести поля и синхронизировать таблицу связи подтверждений."""
        record.requested_id, record.offered_id = exchange.requested_id, exchange.offered_id
        record.sender_login, record.recipient_login = (
            exchange.sender.casefold(),
            exchange.recipient.casefold(),
        )
        record.pair_low, record.pair_high = sorted((exchange.requested_id, exchange.offered_id))
        record.created_at, record.status = exchange.created_at, exchange.status.value
        record.confirmed_by = confirmations

    @staticmethod
    def to_record(exchange: Exchange, confirmations: list[UserRecord]) -> ExchangeRecord:
        """Подготовить новую заявку без ручного назначения ID."""
        record = ExchangeRecord()
        ExchangeMapper.update_record(exchange, record, confirmations)
        return record
