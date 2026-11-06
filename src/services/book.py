from dataclasses import replace

from src.book_models import CONDITIONS, GENRES, Book, BookStatus
from src.exchange_models import ExchangeStatus
from src.repositories.book import BookRepository
from src.repositories.exchange import ExchangeRepository
from src.services.user import UserService


class BookService:
    """Добавлять и изменять собственные объявления по требованиям Ф3–Ф4."""

    def __init__(
        self,
        user_service: UserService,
        book_repository: BookRepository,
        exchange_repository: ExchangeRepository,
    ) -> None:
        """Получить сессию и хранилища для контроля прав и связанных заявок."""
        self._user_service = user_service
        self._book_repository = book_repository
        self._exchange_repository = exchange_repository

    def add(
        self, title: str, author: str, genre: str, condition: str, description: str = ""
    ) -> Book:
        """Создать доступное объявление от имени текущего пользователя."""
        user = self._user_service.require_user()
        self._validate(title, author, genre, condition, description)
        return self._book_repository.add(
            Book(
                0, user.login, title.strip(), author.strip(), genre, condition, description.strip()
            )
        )

    def mine(self) -> list[Book]:
        """Показать все собственные нескрытые объявления, включая занятые."""
        user = self._user_service.require_user()
        return [
            book
            for book in self._book_repository.all()
            if book.owner_login == user.login and not book.deleted
        ]

    def editable(self, book_id: int) -> Book:
        """Проверить владельца и доступность перед изменением объявления."""
        user = self._user_service.require_user()
        book = self._book_repository.get(book_id)
        if book.owner_login != user.login:
            raise PermissionError("Можно изменять только свои объявления.")
        if book.deleted or book.status != BookStatus.AVAILABLE:
            raise ValueError("Изменять можно только доступные объявления.")
        return book

    def edit(
        self, book_id: int, title: str, author: str, genre: str, condition: str, description: str
    ) -> Book:
        """Изменить текстовые поля своего доступного объявления."""
        book = self.editable(book_id)
        self._validate(title, author, genre, condition, description)
        updated = replace(
            book,
            title=title.strip(),
            author=author.strip(),
            genre=genre,
            condition=condition,
            description=description.strip(),
        )
        self._book_repository.save(updated)
        return updated

    def delete(self, book_id: int, confirmed: bool = False) -> bool:
        """После подтверждения скрыть книгу и отменить связанные ожидающие заявки."""
        book = self.editable(book_id)
        if not confirmed:
            return False
        pending = [
            item
            for item in self._exchange_repository.all()
            if item.status == ExchangeStatus.WAITING and book_id in item.book_ids
        ]
        self._book_repository.save(replace(book, deleted=True))
        for item in pending:
            self._exchange_repository.save(replace(item, status=ExchangeStatus.CANCELLED))
        return True

    def _validate(
        self, title: str, author: str, genre: str, condition: str, description: str
    ) -> None:
        """Проверить все поля до изменения хранилища."""
        for label, value in [("Название", title), ("Автор", author)]:
            if not 1 <= len(value.strip()) <= 150:
                raise ValueError(f"{label}: от 1 до 150 символов.")
        if genre not in GENRES:
            raise ValueError("Выберите жанр из списка.")
        if condition not in CONDITIONS:
            raise ValueError("Выберите состояние из списка.")
        if len(description) > 1000:
            raise ValueError("Описание: не более 1000 символов.")
