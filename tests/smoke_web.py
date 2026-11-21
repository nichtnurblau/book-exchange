"""Проверка запущенной Docker-сборки: python -m tests.smoke_web."""

import os
from uuid import uuid4

import httpx


def check() -> None:
    """Выполнить полный обмен через настоящий HTTP-сервер и PostgreSQL."""
    url = os.environ.get("WEB_URL", "http://localhost:8000")
    suffix = uuid4().hex[:10]
    with httpx.Client(base_url=url) as anna, httpx.Client(base_url=url) as boris:

        def post(client: httpx.Client, path: str, **data: object) -> dict:
            token = client.get("/api/session").json()["csrf_token"]
            response = client.post(path, json=data, headers={"X-CSRF-Token": token})
            response.raise_for_status()
            return response.json()

        ids = []
        for client, prefix in [(anna, "anna"), (boris, "boris")]:
            login = prefix + suffix
            post(
                client,
                "/api/users",
                login=login,
                password="testpass123",
                name=prefix,
                city="Волгоград",
                contact=login + "@example.test",
            )
            post(client, "/api/login", login=login, password="testpass123")
            book = post(
                client,
                "/api/books",
                title="Книга " + prefix,
                author="Автор",
                genre="Другое",
                condition="Новое",
            )
            ids.append(book["id"])
            assert client.get("/").status_code == 200
        item = post(anna, "/api/exchanges", requested_id=ids[1], offered_id=ids[0])["exchange"][
            "id"
        ]
        post(boris, f"/api/exchanges/{item}/accept")
        post(anna, f"/api/exchanges/{item}/confirm")
        result = post(boris, f"/api/exchanges/{item}/confirm")
        assert result["exchange"]["status"] == "Завершена"
        assert anna.get("/exchanges").status_code == 200
        assert boris.get("/books").status_code == 200
    print("HTTP, HTML и обмен через PostgreSQL: OK")


if __name__ == "__main__":
    check()
