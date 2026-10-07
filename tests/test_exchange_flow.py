import sys
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from auth import AuthService
from book_models import GENRES, BookStatus
from book_repository import InMemoryBookRepository
from books import BookService
from catalog import CatalogService
from exchange_models import ExchangeStatus
from exchange_repository import InMemoryExchangeRepository
from exchanges import ExchangeService
from models import User
from repositories import InMemoryUserRepository
from security import PasswordHasher


class ExchangeFlowTests(unittest.TestCase):
    """Проверить книги, права и жизненный цикл обмена Ф3–Ф10."""

    @classmethod
    def setUpClass(cls) -> None:
        """Подготовить пароль для вымышленных учётных записей тестов."""
        cls.hasher = PasswordHasher()
        cls.password_hash, cls.salt = cls.hasher.create("testpass123")

    def setUp(self) -> None:
        """Создать три независимых пользователя и по книге у каждого."""
        self.users = InMemoryUserRepository()
        for login, name in [("anna", "Анна"), ("boris", "Борис"), ("vera", "Вера")]:
            self.users.add(
                User(
                    login, name, "Волгоград", f"{login}@example.test", self.password_hash, self.salt
                )
            )
        self.auth = AuthService(self.users, self.hasher)
        self.books = InMemoryBookRepository()
        self.requests = InMemoryExchangeRepository()
        self.service = BookService(self.auth, self.books, self.requests)
        self.exchange = ExchangeService(self.auth, self.books, self.requests, self.users)
        self.catalog = CatalogService(self.books, self.users)
        ids = []
        for login in ("anna", "boris", "vera"):
            self.login(login)
            ids.append(self.service.add(f"Книга {login}", "Автор", GENRES[0], "Хорошее").id)
        self.a, self.b, self.c = ids
        self.login("anna")

    def login(self, login: str) -> None:
        """Переключить текущую сессию штатным входом."""
        self.auth.login(login, "testpass123")

    def accepted(self) -> int:
        """Создать заявку Анны Борису и принять её от имени Бориса."""
        self.login("anna")
        item = self.exchange.send(self.b, self.a)
        self.login("boris")
        self.exchange.accept(item.id)
        return item.id

    def test_add_edit_validation_and_owner(self) -> None:
        """Ф3–Ф4: владелец определяется сессией, поля проверяются до записи."""
        item = self.service.add(" Книга ", " Автор ", GENRES[1], "Новое")
        self.assertEqual(
            (item.owner_login, item.title, item.status), ("anna", "Книга", BookStatus.AVAILABLE)
        )
        for title, author, genre, condition, description in [
            (" ", "Автор", GENRES[0], "Новое", ""),
            ("a" * 151, "Автор", GENRES[0], "Новое", ""),
            ("Книга", "a" * 151, GENRES[0], "Новое", ""),
            ("Книга", "Автор", "левый жанр", "Новое", ""),
            ("Книга", "Автор", GENRES[0], "сломана", ""),
            ("Книга", "Автор", GENRES[0], "Новое", "a" * 1001),
        ]:
            with self.assertRaises(ValueError):
                self.service.edit(item.id, title, author, genre, condition, description)
            self.assertEqual(self.books.get(item.id), item)
        self.service.edit(item.id, "Новое название", "Автор", GENRES[2], "Хорошее", "Описание")
        self.assertEqual(self.books.get(item.id).title, "Новое название")
        with self.assertRaises(PermissionError):
            self.service.edit(self.b, "Подмена", "Автор", GENRES[0], "Новое", "")
        with self.assertRaises(PermissionError):
            self.service.delete(self.b, True)
        with self.assertRaises(ValueError):
            self.service.delete(999, True)
        self.assertTrue(all(book.owner_login == "anna" for book in self.service.mine()))

    def test_guests_cannot_change_data(self) -> None:
        """Выход запрещает все операции зарегистрированного пользователя."""
        item = self.exchange.send(self.b, self.a)
        self.auth.logout()
        actions = [
            lambda: self.service.add("К", "А", GENRES[0], "Новое"),
            lambda: self.service.editable(self.a),
            lambda: self.service.delete(self.a, True),
            self.service.mine,
            lambda: self.exchange.send(self.b, self.a),
            lambda: self.exchange.mine(True),
            lambda: self.exchange.view(item.id),
            lambda: self.exchange.accept(item.id),
            lambda: self.exchange.reject(item.id),
            lambda: self.exchange.cancel(item.id),
            lambda: self.exchange.confirm(item.id),
        ]
        for action in actions:
            with self.assertRaises(PermissionError):
                action()
        self.assertEqual(len(self.catalog.search()), 3)

    def test_duplicates_owners_and_incoming_outgoing(self) -> None:
        """Ф6–Ф7: направление заявки и запрет обратного дубликата."""
        item = self.exchange.send(self.b, self.a)
        self.assertEqual(len(self.exchange.mine(False)), 1)
        self.assertEqual(self.exchange.mine(True), [])
        self.assertIsNotNone(item.created_at.tzinfo)
        with self.assertRaises(ValueError):
            self.exchange.send(self.b, self.a)
        with self.assertRaises(ValueError):
            self.exchange.send(self.a, self.a)
        with self.assertRaises(PermissionError):
            self.exchange.send(self.b, self.c)
        self.login("boris")
        with self.assertRaises(ValueError):
            self.exchange.send(self.a, self.b)
        self.assertEqual(len(self.exchange.mine(True)), 1)
        self.login("vera")
        self.assertEqual(self.exchange.mine(True), [])
        self.assertEqual(self.exchange.mine(False), [])
        for action in (
            self.exchange.view,
            self.exchange.accept,
            self.exchange.reject,
            self.exchange.cancel,
            self.exchange.confirm,
        ):
            with self.assertRaises(PermissionError):
                action(item.id)

    def test_accept_conflicts_on_both_books(self) -> None:
        """Принятие отклоняет предложения, затрагивающие любую из двух книг."""
        main = self.exchange.send(self.b, self.a)
        self.login("vera")
        first = self.exchange.send(self.a, self.c)
        second = self.exchange.send(self.b, self.c)
        self.login("boris")
        self.exchange.accept(main.id)
        self.assertEqual(self.books.get(self.a).status, BookStatus.RESERVED)
        self.assertEqual(self.books.get(self.b).status, BookStatus.RESERVED)
        self.assertEqual(self.books.get(self.c).status, BookStatus.AVAILABLE)
        for item in (first, second):
            self.assertEqual(self.requests.get(item.id).status, ExchangeStatus.REJECTED)
        self.assertEqual([card.book.id for card in self.catalog.search()], [self.c])

    def test_accept_rechecks_before_any_change(self) -> None:
        """Непригодность второй книги не резервирует первую."""
        item = self.exchange.send(self.b, self.a)
        self.books.save(replace(self.books.get(self.a), deleted=True))
        self.login("boris")
        with self.assertRaises(ValueError):
            self.exchange.accept(item.id)
        self.assertEqual(self.books.get(self.b).status, BookStatus.AVAILABLE)
        self.assertEqual(self.requests.get(item.id).status, ExchangeStatus.WAITING)

    def test_only_recipient_can_respond(self) -> None:
        """Отправитель не принимает и не отклоняет своё предложение."""
        item = self.exchange.send(self.b, self.a)
        for action in (self.exchange.accept, self.exchange.reject):
            with self.assertRaises(PermissionError):
                action(item.id)
        self.login("boris")
        with self.assertRaises(PermissionError):
            self.exchange.cancel(item.id)
        self.exchange.reject(item.id)
        self.assertEqual(self.books.get(self.a).status, BookStatus.AVAILABLE)
        self.assertEqual(self.books.get(self.b).status, BookStatus.AVAILABLE)

    def test_delete_requires_confirmation_and_keeps_history(self) -> None:
        """Удаление отменяет ожидающие заявки и сохраняет обе книги в истории."""
        item = self.exchange.send(self.b, self.a)
        self.assertFalse(self.service.delete(self.a))
        self.assertFalse(self.books.get(self.a).deleted)
        self.assertTrue(self.service.delete(self.a, True))
        self.assertEqual(self.service.mine(), [])
        view = self.exchange.view(item.id)
        self.assertEqual(view.exchange.status, ExchangeStatus.CANCELLED)
        self.assertEqual(view.offered.title, "Книга anna")
        self.assertTrue(view.offered.deleted)
        self.assertEqual(len(self.catalog.search()), 2)
        with self.assertRaises(ValueError):
            self.exchange.send(self.b, self.a)
        self.login("boris")
        self.assertEqual(self.exchange.view(item.id).offered.title, "Книга anna")

    def test_pending_cancel_and_repeat_request(self) -> None:
        """Отправитель отменяет ожидающую заявку и может предложить обмен заново."""
        item = self.exchange.send(self.b, self.a)
        self.exchange.cancel(item.id)
        new = self.exchange.send(self.b, self.a)
        self.assertNotEqual(item.id, new.id)
        self.assertEqual(self.books.get(self.b).status, BookStatus.AVAILABLE)

    def test_cancel_accepted_clears_confirmation_and_contacts(self) -> None:
        """Принятый обмен отменяется любым участником, сбрасывая подтверждения."""
        item_id = self.accepted()
        self.exchange.confirm(item_id)
        self.login("anna")
        self.assertEqual(self.exchange.view(item_id).partner_contact, "boris@example.test")
        cancelled = self.exchange.cancel(item_id)
        self.assertEqual(cancelled.confirmations, frozenset())
        self.assertIsNone(self.exchange.view(item_id).partner_contact)
        for book_id in (self.a, self.b):
            self.assertEqual(self.books.get(book_id).status, BookStatus.AVAILABLE)
        new = self.exchange.send(self.b, self.a)
        self.login("boris")
        self.exchange.accept(new.id)
        self.exchange.cancel(new.id)
        self.assertEqual(self.books.get(self.a).status, BookStatus.AVAILABLE)

    def test_conflicts_stay_rejected_after_cancel(self) -> None:
        """Отмена принятого обмена не восстанавливает конкурирующие заявки."""
        first = self.exchange.send(self.b, self.a)
        self.login("vera")
        other = self.exchange.send(self.b, self.c)
        self.login("boris")
        self.exchange.accept(first.id)
        self.exchange.cancel(first.id)
        self.assertEqual(self.requests.get(other.id).status, ExchangeStatus.REJECTED)

    def test_contact_visibility_and_two_confirmations(self) -> None:
        """Контакты закрыты до принятия, завершение требует двух разных участников."""
        item = self.exchange.send(self.b, self.a)
        self.assertIsNone(self.exchange.view(item.id).partner_contact)
        with self.assertRaises(ValueError):
            self.exchange.confirm(item.id)
        self.login("boris")
        self.exchange.accept(item.id)
        self.assertEqual(self.exchange.view(item.id).partner_contact, "anna@example.test")
        self.exchange.confirm(item.id)
        with self.assertRaises(ValueError):
            self.exchange.confirm(item.id)
        self.assertEqual(self.books.get(self.a).status, BookStatus.RESERVED)
        self.login("anna")
        completed = self.exchange.confirm(item.id)
        self.assertEqual(completed.status, ExchangeStatus.COMPLETED)
        self.assertEqual(self.exchange.view(item.id).partner_contact, "boris@example.test")
        for book_id in (self.a, self.b):
            self.assertEqual(self.books.get(book_id).status, BookStatus.EXCHANGED)
        self.assertEqual(len(self.catalog.search()), 1)
        self.login("boris")
        for action in (
            self.exchange.cancel,
            self.exchange.reject,
            self.exchange.accept,
            self.exchange.confirm,
        ):
            with self.assertRaises(ValueError):
                action(item.id)

    def test_busy_books_cannot_be_edited_deleted_or_offered(self) -> None:
        """Ограничения действуют и после резерва, и после завершения."""
        item_id = self.accepted()
        for complete in (False, True):
            if complete:
                self.exchange.confirm(item_id)
                self.login("anna")
                self.exchange.confirm(item_id)
            for login, book_id in [("anna", self.a), ("boris", self.b)]:
                self.login(login)
                with self.assertRaises(ValueError):
                    self.service.editable(book_id)
                with self.assertRaises(ValueError):
                    self.service.delete(book_id, True)
                with self.assertRaises(ValueError):
                    self.exchange.send(self.c, book_id)
                self.assertEqual(len(self.service.mine()), 1)

    def test_unknown_ids_and_new_stores(self) -> None:
        """Неизвестные ID дают понятные ошибки, новые хранилища пусты."""
        with self.assertRaises(ValueError):
            self.exchange.send(999, self.a)
        with self.assertRaises(ValueError):
            self.exchange.view(999)
        self.assertEqual(InMemoryBookRepository().all(), [])
        self.assertEqual(InMemoryExchangeRepository().all(), [])


if __name__ == "__main__":
    unittest.main()
