import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from alembic import command
from sqlalchemy import func, inspect, select

from src.book_models import GENRES, Book, BookStatus
from src.database.models import BookRecord, ExchangeConfirmation, ExchangeRecord, UserRecord
from src.database.repositories.book import SQLAlchemyBookRepository
from src.database.repositories.exchange import SQLAlchemyExchangeRepository
from src.database.repositories.user import SQLAlchemyUserRepository
from src.database.session import Database
from src.exchange_models import ExchangeStatus
from src.security import PasswordHasher
from src.services.book import BookService
from src.services.exchange import ExchangeService
from src.services.user import UserService
from tests.db_support import migrate, migration_config


class DatabaseTests(unittest.TestCase):
    """Проверить сохранение, ограничения, связи, каскады и откат транзакций."""

    def setUp(self) -> None:
        """Создать отдельную тестовую схему через Alembic."""
        self.url = self.make_database_url()
        migrate(self.url)
        self.database = Database(self.url)
        self.addCleanup(self.database.close)
        self.user_repository = SQLAlchemyUserRepository(self.database.session)
        self.book_repository = SQLAlchemyBookRepository(self.database.session)
        self.exchange_repository = SQLAlchemyExchangeRepository(self.database.session)
        self.user_service = UserService(self.user_repository, PasswordHasher())
        self.book_service = BookService(
            self.user_service, self.book_repository, self.exchange_repository
        )
        self.exchange_service = ExchangeService(
            self.user_service, self.book_repository, self.exchange_repository, self.user_repository
        )

    def make_database_url(self) -> str:
        """Выделить отдельный SQLite-файл для одного теста."""
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        return "sqlite:///" + str(Path(folder.name) / "test.db")

    def prepare_exchange(self) -> int:
        """Создать две книги и ожидающее предложение в одной транзакции."""
        with self.database.transaction():
            for login in ("Anna", "Boris"):
                self.user_service.register(
                    login, "testpass123", login, "Волгоград", login + "@example.test"
                )
                self.user_service.login(login, "testpass123")
                self.book_service.add("Книга " + login, "Автор", GENRES[0], "Новое")
            return self.exchange_service.send(1, 2).id

    def test_new_user_is_saved_without_outer_commit(self) -> None:
        """Новый пользователь сохраняется самим методом добавления."""
        self.user_service.register("Anna", "testpass123", "Анна", "Волгоград", "contact")
        self.database.close()
        other = Database(self.url)
        try:
            with other.transaction():
                user = SQLAlchemyUserRepository(other.session).find_by_login("anna")
                self.assertIsNotNone(user)
                self.assertEqual(user.name, "Анна")
        finally:
            other.close()

    def test_new_book_is_saved_without_outer_commit(self) -> None:
        """Новая книга с выданным БД ID доступна после закрытия сессии."""
        self.user_service.register("Anna", "testpass123", "Анна", "Волгоград", "contact")
        self.user_service.login("anna", "testpass123")
        book = self.book_service.add("Книга", "Автор", GENRES[0], "Новое")
        self.database.close()
        other = Database(self.url)
        try:
            with other.transaction():
                saved = SQLAlchemyBookRepository(other.session).get(book.id)
                self.assertGreater(saved.id, 0)
                self.assertEqual(saved.title, "Книга")
                self.assertEqual(saved.owner_login, "Anna")
        finally:
            other.close()

    def test_persistence_and_casefold(self) -> None:
        """Новая сессия читает прежние записи с исходным регистром логина."""
        self.prepare_exchange()
        other = Database(self.url)
        try:
            with other.transaction():
                user = SQLAlchemyUserRepository(other.session).find_by_login("ANNA")
                self.assertEqual(user.login, "Anna")
                self.assertEqual(len(SQLAlchemyBookRepository(other.session).all()), 2)
                self.assertEqual(len(SQLAlchemyExchangeRepository(other.session).all()), 1)
        finally:
            other.close()

    def test_rollback_if_second_book_save_fails(self) -> None:
        """Сбой после обновления первой книги откатывает весь приём заявки."""
        item_id = self.prepare_exchange()
        original = self.book_repository.save
        calls = 0

        def fail_on_second(book: Book) -> None:
            """Имитировать отказ хранилища в середине операции."""
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("Искусственный сбой")
            original(book)

        with (
            self.assertRaises(RuntimeError),
            patch.object(self.book_repository, "save", side_effect=fail_on_second),
        ):
            with self.database.transaction():
                self.user_service.login("anna", "testpass123")
                self.exchange_service.accept(item_id)
        with self.database.transaction():
            self.assertTrue(
                all(book.status == BookStatus.AVAILABLE for book in self.book_repository.all())
            )
            self.assertEqual(self.exchange_repository.get(item_id).status, ExchangeStatus.WAITING)

    def test_relationships_and_confirmation_cascade(self) -> None:
        """Связи 1:N и M:N доступны в ORM; удаление заявки удаляет только связи."""
        item_id = self.prepare_exchange()
        with self.database.transaction():
            self.user_service.login("anna", "testpass123")
            self.exchange_service.accept(item_id)
            self.exchange_service.confirm(item_id)
            self.user_service.login("boris", "testpass123")
            self.exchange_service.confirm(item_id)
        with self.database.transaction():
            anna = self.database.session.get(UserRecord, "anna")
            item = self.database.session.get(ExchangeRecord, item_id)
            self.assertEqual(len(anna.books), 1)
            self.assertEqual(len(anna.confirmed_exchanges), 1)
            self.assertEqual({user.login for user in item.confirmed_by}, {"anna", "boris"})
            self.database.session.delete(item)
        with self.database.transaction():
            self.assertEqual(
                self.database.session.scalar(
                    select(func.count()).select_from(ExchangeConfirmation)
                ),
                0,
            )
            self.assertEqual(len(self.book_repository.all()), 2)
            self.assertIsNotNone(self.user_repository.find_by_login("anna"))

    def test_foreign_keys_and_restrict(self) -> None:
        """Ссылка на отсутствующего владельца и удаление владельца книги запрещены."""
        self.prepare_exchange()
        with self.assertRaises(ValueError):
            with self.database.transaction():
                self.database.session.delete(self.database.session.get(UserRecord, "anna"))
        with self.assertRaises(ValueError):
            with self.database.transaction():
                record = self.database.session.get(BookRecord, 1)
                record.owner_login = "missing"
                self.database.session.flush()
        with self.database.transaction():
            self.assertEqual(self.book_repository.get(1).owner_login, "Anna")

    def test_partial_unique_index_blocks_reverse_pair(self) -> None:
        """Активный обратный дубликат блокируется даже без сервиса."""
        item_id = self.prepare_exchange()
        with self.assertRaises(ValueError):
            with self.database.transaction():
                item = self.database.session.get(ExchangeRecord, item_id)
                self.database.session.add(
                    ExchangeRecord(
                        requested_id=2,
                        offered_id=1,
                        sender_login="anna",
                        recipient_login="boris",
                        pair_low=1,
                        pair_high=2,
                        created_at=item.created_at,
                        status="Ожидает ответа",
                    )
                )
                self.database.session.flush()
        with self.database.transaction():
            self.assertEqual(len(self.exchange_repository.all()), 1)

    def test_migration_roundtrip(self) -> None:
        """Downgrade убирает таблицы, upgrade восстанавливает схему без расхождений."""
        self.database.close()
        with patch.dict(os.environ, {"DATABASE_URL": self.url}):
            config = migration_config()
            command.check(config)
            command.downgrade(config, "base")
            self.assertNotIn("books", inspect(self.database.engine).get_table_names())
            command.upgrade(config, "head")
            command.check(config)
        self.database.check_schema()
