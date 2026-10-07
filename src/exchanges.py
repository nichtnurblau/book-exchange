from dataclasses import dataclass, replace
from datetime import datetime, timezone

from auth import AuthService
from book_models import Book, BookStatus
from book_repository import BookRepository
from exchange_models import Exchange, ExchangeStatus
from exchange_repository import ExchangeRepository
from repositories import UserRepository


@dataclass(frozen=True)
class ExchangeView:
    """Данные заявки для участника с контролируемым раскрытием контакта."""

    exchange: Exchange
    requested: Book
    offered: Book
    partner_name: str
    partner_contact: str | None


class ExchangeService:
    """Выполнять переходы состояний заявки и проверки доступа Ф6–Ф10."""

    def __init__(
        self,
        auth: AuthService,
        books: BookRepository,
        exchanges: ExchangeRepository,
        users: UserRepository,
    ) -> None:
        """Получить сессию и хранилища через параметры конструктора."""
        self._auth = auth
        self._books = books
        self._exchanges = exchanges
        self._users = users

    def _available(self, book_id: int) -> Book:
        """Проверить, что книга существует, не скрыта и доступна."""
        book = self._books.get(book_id)
        if book.deleted or book.status != BookStatus.AVAILABLE:
            raise ValueError("Обе книги должны быть доступны для обмена.")
        return book

    def _participant(self, exchange_id: int) -> Exchange:
        """Разрешить доступ к заявке только одному из её участников."""
        user = self._auth.require_user()
        item = self._exchanges.get(exchange_id)
        if user.login not in (item.sender, item.recipient):
            raise PermissionError("Эта заявка вам недоступна.")
        return item

    def send(self, requested_id: int, offered_id: int) -> Exchange:
        """Создать предложение, проверив владельцев, доступность и дубликаты."""
        user = self._auth.require_user()
        requested = self._available(requested_id)
        offered = self._available(offered_id)
        if requested.owner_login == user.login:
            raise ValueError("Нельзя отправить заявку на собственную книгу.")
        if offered.owner_login != user.login:
            raise PermissionError("Можно предложить только свою книгу.")
        pair = frozenset((requested_id, offered_id))
        for item in self._exchanges.all():
            if item.book_ids == pair and item.status in (
                ExchangeStatus.WAITING,
                ExchangeStatus.ACCEPTED,
            ):
                raise ValueError("Для этой пары книг уже есть действующая заявка.")
        return self._exchanges.add(
            Exchange(
                0,
                requested_id,
                offered_id,
                user.login,
                requested.owner_login,
                datetime.now(timezone.utc),
            )
        )

    def mine(self, incoming: bool) -> list[ExchangeView]:
        """Вернуть входящие либо исходящие заявки текущего пользователя."""
        user = self._auth.require_user()
        return [
            self.view(item.id)
            for item in self._exchanges.all()
            if (item.recipient if incoming else item.sender) == user.login
        ]

    def view(self, exchange_id: int) -> ExchangeView:
        """Открыть свою заявку, раскрывая контакт только после принятия."""
        item = self._participant(exchange_id)
        user = self._auth.require_user()
        partner_login = item.recipient if user.login == item.sender else item.sender
        partner = self._users.find_by_login(partner_login)
        if partner is None:
            raise ValueError("Участник заявки не найден.")
        contact = (
            partner.contact
            if item.status in (ExchangeStatus.ACCEPTED, ExchangeStatus.COMPLETED)
            else None
        )
        return ExchangeView(
            item,
            self._books.get(item.requested_id),
            self._books.get(item.offered_id),
            partner.name,
            contact,
        )

    def _waiting_recipient(self, exchange_id: int) -> Exchange:
        """Проверить право получателя ответить на ожидающую заявку."""
        item = self._participant(exchange_id)
        if self._auth.require_user().login != item.recipient:
            raise PermissionError("Ответить на заявку может только получатель.")
        if item.status != ExchangeStatus.WAITING:
            raise ValueError("Ответ возможен только на ожидающую заявку.")
        return item

    def accept(self, exchange_id: int) -> Exchange:
        """Зарезервировать обе книги и отклонить остальные ожидающие предложения к ним."""
        item = self._waiting_recipient(exchange_id)
        requested = self._available(item.requested_id)
        offered = self._available(item.offered_id)
        conflicts = [
            other
            for other in self._exchanges.all()
            if other.id != item.id
            and other.status == ExchangeStatus.WAITING
            and other.book_ids & item.book_ids
        ]
        updated = replace(item, status=ExchangeStatus.ACCEPTED)
        self._books.save(replace(requested, status=BookStatus.RESERVED))
        self._books.save(replace(offered, status=BookStatus.RESERVED))
        self._exchanges.save(updated)
        for other in conflicts:
            self._exchanges.save(replace(other, status=ExchangeStatus.REJECTED))
        return updated

    def reject(self, exchange_id: int) -> Exchange:
        """Отклонить ожидающее предложение без изменения доступности книг."""
        item = self._waiting_recipient(exchange_id)
        updated = replace(item, status=ExchangeStatus.REJECTED)
        self._exchanges.save(updated)
        return updated

    def cancel(self, exchange_id: int) -> Exchange:
        """Отменить заявку с проверкой прав, освободив книги принятого обмена."""
        item = self._participant(exchange_id)
        user = self._auth.require_user()
        if item.status == ExchangeStatus.WAITING:
            if user.login != item.sender:
                raise PermissionError("Ожидающую заявку может отменить только отправитель.")
        elif item.status == ExchangeStatus.ACCEPTED:
            books = [self._books.get(book_id) for book_id in (item.requested_id, item.offered_id)]
            for book in books:
                self._books.save(replace(book, status=BookStatus.AVAILABLE))
        else:
            raise ValueError("Эту заявку уже нельзя отменить.")
        updated = replace(item, status=ExchangeStatus.CANCELLED, confirmations=frozenset())
        self._exchanges.save(updated)
        return updated

    def confirm(self, exchange_id: int) -> Exchange:
        """Завершить обмен только после отдельных подтверждений обоих участников."""
        item = self._participant(exchange_id)
        user = self._auth.require_user()
        if item.status != ExchangeStatus.ACCEPTED:
            raise ValueError("Подтверждать можно только принятый обмен.")
        if user.login in item.confirmations:
            raise ValueError("Вы уже подтвердили передачу.")
        confirmations = item.confirmations | frozenset((user.login,))
        status = ExchangeStatus.COMPLETED if len(confirmations) == 2 else ExchangeStatus.ACCEPTED
        updated = replace(item, status=status, confirmations=confirmations)
        if status == ExchangeStatus.COMPLETED:
            books = [self._books.get(book_id) for book_id in (item.requested_id, item.offered_id)]
            for book in books:
                self._books.save(replace(book, status=BookStatus.EXCHANGED))
        self._exchanges.save(updated)
        return updated
