import re
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.web.app import create_app
from tests.db_support import migrate


class PageTests(unittest.TestCase):
    """Проверки HTML-форм и работы с существующими сервисами."""

    def setUp(self) -> None:
        """Создать отдельное приложение с мигрированной БД."""
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        url = "sqlite:///" + str(Path(folder.name) / "pages.db")
        migrate(url)
        self.client = TestClient(create_app(url, secret_key="page-test-key"))
        self.addCleanup(self.client.close)

    def csrf(self, page: str) -> str:
        """Прочитать токен скрытого поля HTML-формы."""
        text = self.client.get(page).text
        match = re.search(r'name="csrf" value="([^"]+)"', text)
        self.assertIsNotNone(match, text)
        return match.group(1)

    def register_and_login(self) -> None:
        """Пройти регистрацию и вход через HTML-формы."""
        response = self.client.post(
            "/register",
            data=dict(
                csrf=self.csrf("/register"),
                login="reader",
                password="testpass123",
                name="Читатель",
                city="Волгоград",
                contact="contact",
            ),
        )
        self.assertEqual(response.status_code, 200, response.text)
        response = self.client.post(
            "/login", data=dict(csrf=self.csrf("/login"), login="reader", password="testpass123")
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("Читатель", response.text)

    def test_catalog_and_forms(self) -> None:
        """Страницы показываются; создание, изменение и удаление работают."""
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/static/style.css").status_code, 200)
        self.register_and_login()
        token = self.csrf("/books/new")
        data = dict(
            csrf=token,
            title="<script>alert(1)</script>",
            author="Автор",
            genre="Другое",
            condition="Новое",
            description="Описание",
        )
        response = self.client.post("/books/save", data=data)
        self.assertEqual(response.status_code, 200, response.text)
        catalog = self.client.get("/").text
        self.assertIn("&lt;script&gt;", catalog)
        self.assertNotIn("<script>alert(1)</script>", catalog)
        self.assertEqual(self.client.get("/books/1/edit").status_code, 200)
        data.update(book_id=1, title="Новое название")
        self.assertEqual(self.client.post("/books/save", data=data).status_code, 200)
        response = self.client.post("/books/1/delete", data={"csrf": token})
        self.assertIn("У вас пока нет книг", response.text)

    def test_invalid_login_and_csrf(self) -> None:
        """Ошибки формы не создают сессию, отсутствие CSRF запрещает запрос."""
        token = self.csrf("/login")
        response = self.client.post(
            "/login", data={"csrf": token, "login": "missing", "password": "badpass123"}
        )
        self.assertIn("Неверный логин или пароль", response.text)
        self.assertNotIn("badpass123", response.text)
        self.assertEqual(self.client.post("/logout").status_code, 422)
        self.assertEqual(self.client.post("/logout", data={"csrf": "wrong"}).status_code, 403)
        self.assertEqual(self.client.get("/books").status_code, 403)

    def test_routes_share_exchange_command(self) -> None:
        """Входящие и исходящие страницы доступны после входа."""
        self.register_and_login()
        response = self.client.get("/exchanges")
        self.assertIn("Входящие", response.text)
        self.assertIn("Исходящие", response.text)
        response = self.client.post("/logout", data={"csrf": self.csrf("/exchanges")})
        self.assertIn("Войти", response.text)
        self.assertEqual(self.client.get("/books").status_code, 403)
