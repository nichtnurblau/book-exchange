from collections.abc import Iterator
from secrets import compare_digest, token_urlsafe
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from src.database.session import Database
from src.services.factory import ServiceFactory


def csrf_token(request: Request) -> str:
    """Создать токен в подписанной сессии для защиты изменяющих запросов."""
    if "csrf" not in request.session:
        request.session["csrf"] = token_urlsafe(24)
    return request.session["csrf"]


def get_services(request: Request) -> Iterator[ServiceFactory]:
    """Открыть Unit of Work и сохранить изменения до отправки ответа."""
    database = Database(request.app.state.database_url)
    try:
        with database.transaction():
            services = ServiceFactory(database.session)
            if login := request.session.get("login"):
                services.user_service.restore_session(login)
            yield services
    finally:
        database.close()


def require_csrf(request: Request) -> None:
    """Проверить заголовок API; HTML-формы проверяют скрытое поле отдельно."""
    supplied = request.headers.get("X-CSRF-Token", "")
    verify_csrf(request, supplied)


def verify_csrf(request: Request, supplied: str) -> None:
    """Сравнить переданный токен с токеном подписанной сессии."""
    expected = request.session.get("csrf", "")
    if not expected or not compare_digest(expected, supplied):
        raise HTTPException(status_code=403, detail="Обновите страницу и повторите действие.")


Services = Annotated[ServiceFactory, Depends(get_services, scope="function")]
