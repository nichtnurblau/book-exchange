from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from src.dtos.requests import BookRequest, RegistrationRequest
from src.models.book import CONDITIONS, GENRES
from src.services.commands import ExchangeAction, ExchangeCommand
from src.web.dependencies import Services, csrf_token, verify_csrf

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))


def render(request: Request, services: Services, template: str, **context: object) -> HTMLResponse:
    """Добавить к странице пользователя и токен форм."""
    return templates.TemplateResponse(
        request=request,
        name=template,
        context={
            "user": services.user_service.current_user,
            "csrf": csrf_token(request),
            "genres": GENRES,
            "conditions": CONDITIONS,
            **context,
        },
    )


def redirect(path: str) -> RedirectResponse:
    """Перейти на GET-страницу после изменения данных."""
    return RedirectResponse(path, status_code=303)


@router.get("/", response_class=HTMLResponse)
def catalog(
    request: Request, services: Services, query: str = "", genre: str = "", city: str = ""
) -> HTMLResponse:
    """Показать каталог с поиском и фильтрами."""
    return render(
        request,
        services,
        "catalog.html",
        cards=services.catalog_service.search(query, genre, city),
        query=query,
        genre=genre,
        city=city,
        own_books=services.book_service.mine() if services.user_service.current_user else [],
    )


@router.get("/register", response_class=HTMLResponse)
def registration_page(request: Request, services: Services) -> HTMLResponse:
    """Показать форму регистрации."""
    return render(request, services, "auth.html", register=True, error="")


@router.post("/register", response_class=HTMLResponse)
def register(
    request: Request,
    services: Services,
    csrf: str = Form(...),
    login: str = Form(...),
    password: str = Form(...),
    name: str = Form(...),
    city: str = Form(...),
    contact: str = Form(...),
) -> HTMLResponse:
    """Проверить форму и создать учётную запись."""
    verify_csrf(request, csrf)
    try:
        data = RegistrationRequest(
            login=login, password=password, name=name, city=city, contact=contact
        )
        services.user_service.register(**data.model_dump())
    except ValidationError:
        return render(
            request,
            services,
            "auth.html",
            register=True,
            error="Проверьте длину полей и формат логина.",
        )
    except ValueError as error:
        return render(request, services, "auth.html", register=True, error=str(error))
    return redirect("/login")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, services: Services) -> HTMLResponse:
    """Показать форму входа."""
    return render(request, services, "auth.html", register=False, error="")


@router.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    services: Services,
    csrf: str = Form(...),
    login: str = Form(...),
    password: str = Form(...),
) -> HTMLResponse:
    """Начать подписанную сессию после проверки пароля."""
    verify_csrf(request, csrf)
    request.session.pop("login", None)
    try:
        user = services.user_service.login(login, password)
    except ValueError as error:
        return render(request, services, "auth.html", register=False, error=str(error))
    request.session["login"] = user.login
    return redirect("/")


@router.post("/logout")
def logout(request: Request, csrf: str = Form(...)) -> RedirectResponse:
    """Завершить сессию после проверки токена формы."""
    verify_csrf(request, csrf)
    request.session.clear()
    return redirect("/")


@router.get("/books", response_class=HTMLResponse)
def my_books(request: Request, services: Services) -> HTMLResponse:
    """Показать собственные объявления."""
    return render(request, services, "books.html", books=services.book_service.mine())


@router.get("/books/new", response_class=HTMLResponse)
def new_book(request: Request, services: Services) -> HTMLResponse:
    """Показать форму добавления книги."""
    services.user_service.require_user()
    return render(request, services, "book_form.html", book=None, error="")


@router.get("/books/{book_id}/edit", response_class=HTMLResponse)
def edit_page(book_id: int, request: Request, services: Services) -> HTMLResponse:
    """Открыть редактирование своей доступной книги."""
    return render(
        request, services, "book_form.html", book=services.book_service.editable(book_id), error=""
    )


@router.post("/books/save")
def save_book(
    request: Request,
    services: Services,
    csrf: str = Form(...),
    book_id: int = Form(0),
    title: str = Form(...),
    author: str = Form(...),
    genre: str = Form(...),
    condition: str = Form(...),
    description: str = Form(""),
) -> RedirectResponse:
    """Добавить или изменить объявление через прежний сервис."""
    verify_csrf(request, csrf)
    data = BookRequest(
        title=title, author=author, genre=genre, condition=condition, description=description
    )
    if book_id:
        services.book_service.edit(book_id, **data.model_dump())
    else:
        services.book_service.add(**data.model_dump())
    return redirect("/books")


@router.post("/books/{book_id}/delete")
def delete_book(
    book_id: int, request: Request, services: Services, csrf: str = Form(...)
) -> RedirectResponse:
    """Скрыть своё объявление."""
    verify_csrf(request, csrf)
    services.book_service.delete(book_id, confirmed=True)
    return redirect("/books")


@router.get("/exchanges", response_class=HTMLResponse)
def exchanges(request: Request, services: Services) -> HTMLResponse:
    """Показать обе группы заявок текущего пользователя."""
    return render(
        request,
        services,
        "exchanges.html",
        incoming=services.exchange_service.mine(True),
        outgoing=services.exchange_service.mine(False),
    )


@router.post("/exchanges")
def send_exchange(
    request: Request,
    services: Services,
    csrf: str = Form(...),
    requested_id: int = Form(...),
    offered_id: int = Form(...),
) -> RedirectResponse:
    """Предложить свою книгу в обмен на выбранную."""
    verify_csrf(request, csrf)
    services.exchange_service.send(requested_id, offered_id)
    return redirect("/exchanges")


@router.post("/exchanges/{exchange_id}/{action}")
def act(
    exchange_id: int,
    action: ExchangeAction,
    request: Request,
    services: Services,
    csrf: str = Form(...),
) -> RedirectResponse:
    """Выполнить команду обмена из HTML-формы."""
    verify_csrf(request, csrf)
    ExchangeCommand(services.exchange_service, action, exchange_id).execute()
    return redirect("/exchanges")
