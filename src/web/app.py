import os
from pathlib import Path
from secrets import token_urlsafe

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from src.database.settings import get_database_url
from src.web.api import router
from src.web.pages import router as pages_router


def create_app(database_url: str | None = None, secret_key: str | None = None) -> FastAPI:
    """Собрать HTTP API с отдельной сессией БД для каждого запроса."""
    app = FastAPI(title="Книгообмен", version="0.2.0")
    app.state.database_url = database_url or get_database_url()
    app.add_middleware(
        SessionMiddleware,
        secret_key=secret_key or os.environ.get("APP_SECRET_KEY") or token_urlsafe(32),
        same_site="lax",
        max_age=86400,
    )
    app.include_router(router)
    app.include_router(pages_router)
    app.mount(
        "/static",
        StaticFiles(directory=Path(__file__).resolve().parents[1] / "static"),
        name="static",
    )

    @app.exception_handler(ValueError)
    async def invalid_value(request: Request, error: ValueError) -> JSONResponse:
        """Вывести ошибку бизнес-правила без трассировки."""
        return JSONResponse(status_code=400, content={"detail": str(error)})

    @app.exception_handler(PermissionError)
    async def forbidden(request: Request, error: PermissionError) -> JSONResponse:
        """Сообщить о недоступном действии."""
        return JSONResponse(status_code=403, content={"detail": str(error)})

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, error: RequestValidationError) -> JSONResponse:
        """Вернуть поля с ошибками без исходных значений и паролей."""
        errors = [{"loc": list(item["loc"]), "msg": item["msg"]} for item in error.errors()]
        return JSONResponse(status_code=422, content={"detail": errors})

    return app
