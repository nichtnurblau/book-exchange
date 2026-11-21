import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.models.book import GENRES
from src.repositories.book import SQLAlchemyBookRepository
from src.web.app import create_app
from tests.db_support import migrate


class ApiTests(unittest.TestCase):
    """Проверки HTTP API, сессий, прав доступа и транзакций."""

    def setUp(self) -> None:
        """Подготовить отдельную мигрированную БД и независимых клиентов."""
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.url = "sqlite:///" + str(Path(folder.name) / "api.db")
        migrate(self.url)
        self.app = create_app(self.url, secret_key="test-session-key")
        self.anna = TestClient(self.app)
        self.boris = TestClient(self.app)
        self.addCleanup(self.anna.close)
        self.addCleanup(self.boris.close)

    def post(self, client: TestClient, path: str, **data: object):
        """Отправить JSON с токеном сессии клиента."""
        csrf = client.get("/api/session").json()["csrf_token"]
        return client.post(path, json=data, headers={"X-CSRF-Token": csrf})

    def register(self, client: TestClient, login: str) -> None:
        """Создать пользователя и войти под ним."""
        data = dict(
            login=login,
            password="testpass123",
            name=login,
            city="Волгоград",
            contact=login + "@example.test",
        )
        result = self.post(client, "/api/users", **data)
        self.assertEqual(result.status_code, 201, result.text)
        self.assertNotIn("password", result.text)
        result = self.post(client, "/api/login", login=login, password="testpass123")
        self.assertEqual(result.status_code, 200, result.text)

    def book(self, client: TestClient, title: str) -> int:
        """Добавить одну книгу."""
        result = self.post(
            client, "/api/books", title=title, author="Автор", genre=GENRES[0], condition="Новое"
        )
        self.assertEqual(result.status_code, 201, result.text)
        return result.json()["id"]

    def prepare_exchange(self) -> int:
        """Подготовить ожидающую заявку двух пользователей."""
        self.register(self.anna, "anna")
        a = self.book(self.anna, "Белый клык")
        self.register(self.boris, "boris")
        b = self.book(self.boris, "Алгебра")
        result = self.post(self.anna, "/api/exchanges", requested_id=b, offered_id=a)
        self.assertEqual(result.status_code, 201, result.text)
        return result.json()["exchange"]["id"]

    def test_full_exchange_and_privacy(self) -> None:
        """Обмен завершается двумя участниками; контакты скрыты до принятия."""
        item = self.prepare_exchange()
        catalog = self.anna.get("/api/catalog").json()
        self.assertNotIn("contact", str(catalog))
        self.assertNotIn("password_hash", str(catalog))
        self.assertIsNone(self.anna.get(f"/api/exchanges/{item}").json()["partner_contact"])
        result = self.post(self.boris, f"/api/exchanges/{item}/accept")
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["partner_contact"], "anna@example.test")
        self.post(self.anna, f"/api/exchanges/{item}/confirm")
        result = self.post(self.boris, f"/api/exchanges/{item}/confirm")
        self.assertEqual(result.json()["exchange"]["status"], "Завершена")
        self.assertEqual(self.anna.get("/api/catalog").json(), [])
        self.assertEqual(self.anna.get("/api/session").json()["user"]["login"], "anna")
        self.assertEqual(self.boris.get("/api/session").json()["user"]["login"], "boris")

    def test_guests_and_csrf(self) -> None:
        """Гость не меняет данные; запрос без CSRF отклоняется."""
        self.assertEqual(self.anna.get("/api/books").status_code, 403)
        self.assertEqual(self.anna.post("/api/users", json={}).status_code, 403)
        self.assertEqual(
            self.post(
                self.anna,
                "/api/books",
                title="Книга",
                author="Автор",
                genre=GENRES[0],
                condition="Новое",
            ).status_code,
            403,
        )

    def test_validation_does_not_echo_password(self) -> None:
        """Ошибки входного DTO не возвращают пароль и произвольные поля."""
        response = self.post(
            self.anna, "/api/users", login="ab", password="secret", name="A", city="B", contact="C"
        )
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("secret", response.text)
        self.register(self.anna, "anna")
        response = self.post(
            self.anna,
            "/api/books",
            title="Книга",
            author="Автор",
            genre=GENRES[0],
            condition="Новое",
            owner_login="boris",
        )
        self.assertEqual(response.status_code, 422)

    def test_ownership_and_search(self) -> None:
        """Владелец задаётся сессией, чужое объявление нельзя удалить."""
        self.register(self.anna, "anna")
        item = self.book(self.anna, "Белый клык")
        self.register(self.boris, "boris")
        csrf = self.boris.get("/api/session").json()["csrf_token"]
        self.assertEqual(
            self.boris.delete(f"/api/books/{item}", headers={"X-CSRF-Token": csrf}).status_code, 403
        )
        self.assertEqual(
            len(
                self.boris.get(
                    "/api/catalog", params={"query": "БЕЛЫЙ", "city": "волгоград"}
                ).json()
            ),
            1,
        )

    def test_failure_rolls_back_both_books(self) -> None:
        """Отказ хранилища после первого обновления откатывает HTTP-команду."""
        item = self.prepare_exchange()
        save = SQLAlchemyBookRepository.save
        count = 0

        def fail(repository, book):
            nonlocal count
            count += 1
            if count == 2:
                raise ValueError("Ошибка сохранения второй книги")
            save(repository, book)

        with patch.object(SQLAlchemyBookRepository, "save", new=fail):
            result = self.post(self.boris, f"/api/exchanges/{item}/accept")
        self.assertEqual(result.status_code, 400, result.text)
        self.assertEqual(len(self.anna.get("/api/catalog").json()), 2)
        self.assertEqual(
            self.anna.get(f"/api/exchanges/{item}").json()["exchange"]["status"], "Ожидает ответа"
        )

    def test_cookie_tampering_does_not_authorize(self) -> None:
        """Изменённая cookie не открывает чужую учётную запись."""
        self.register(self.anna, "anna")
        self.boris.cookies.set("session", "forged-session")
        self.assertEqual(self.boris.get("/api/books").status_code, 403)

    def test_repositories_defer_commit_in_http_unit_of_work(self) -> None:
        """Добавленные через HTTP-фабрику записи откатываются при ошибке команды."""
        from src.database.session import Database
        from src.services.factory import ServiceFactory

        database = Database(self.url)
        try:
            with self.assertRaises(ValueError):
                with database.transaction():
                    services = ServiceFactory(database.session)
                    services.user_service.register(
                        "reader", "testpass123", "Имя", "Город", "contact"
                    )
                    raise ValueError("Отмена")
            with database.transaction():
                from src.repositories.user import SQLAlchemyUserRepository

                self.assertIsNone(
                    SQLAlchemyUserRepository(database.session).find_by_login("reader")
                )
        finally:
            database.close()
