from fastapi import APIRouter, Depends, Request

from src.dtos.requests import BookRequest, ExchangeRequest, LoginRequest, RegistrationRequest
from src.dtos.responses import (
    BookResponse,
    CardResponse,
    ExchangeViewResponse,
    MessageResponse,
    SessionResponse,
    UserResponse,
)
from src.services.commands import ExchangeAction, ExchangeCommand
from src.web.dependencies import Services, csrf_token, require_csrf

router = APIRouter(prefix="/api")
write = [Depends(require_csrf)]


@router.get("/session", response_model=SessionResponse)
def session_info(request: Request, services: Services) -> SessionResponse:
    """Вернуть собственную сессию и токен для последующих запросов."""
    user = services.user_service.current_user
    return SessionResponse(
        user=UserResponse.model_validate(user) if user else None, csrf_token=csrf_token(request)
    )


@router.post("/users", response_model=UserResponse, status_code=201, dependencies=write)
def register(data: RegistrationRequest, services: Services) -> UserResponse:
    """Создать пользователя через прежние проверки сервисного слоя."""
    return UserResponse.model_validate(services.user_service.register(**data.model_dump()))


@router.post("/login", response_model=UserResponse, dependencies=write)
def login(data: LoginRequest, request: Request, services: Services) -> UserResponse:
    """Проверить пароль и сохранить логин в подписанной cookie."""
    request.session.pop("login", None)
    user = services.user_service.login(data.login, data.password)
    request.session["login"] = user.login
    return UserResponse.model_validate(user)


@router.post("/logout", response_model=MessageResponse, dependencies=write)
def logout(request: Request) -> MessageResponse:
    """Удалить данные сессии из cookie."""
    request.session.clear()
    return MessageResponse(message="Вы вышли из учётной записи.")


@router.get("/catalog", response_model=list[CardResponse])
def catalog(
    services: Services, query: str = "", genre: str = "", city: str = ""
) -> list[CardResponse]:
    """Найти доступные объявления без контактов владельцев."""
    return [
        CardResponse.model_validate(card)
        for card in services.catalog_service.search(query, genre, city)
    ]


@router.get("/catalog/{book_id}", response_model=CardResponse)
def card(book_id: int, services: Services) -> CardResponse:
    """Открыть доступную карточку."""
    return CardResponse.model_validate(services.catalog_service.get_card(book_id))


@router.get("/books", response_model=list[BookResponse])
def my_books(services: Services) -> list[BookResponse]:
    """Вернуть объявления текущего пользователя."""
    return [BookResponse.model_validate(book) for book in services.book_service.mine()]


@router.post("/books", response_model=BookResponse, status_code=201, dependencies=write)
def add_book(data: BookRequest, services: Services) -> BookResponse:
    """Добавить книгу от имени пользователя сессии."""
    return BookResponse.model_validate(services.book_service.add(**data.model_dump()))


@router.put("/books/{book_id}", response_model=BookResponse, dependencies=write)
def edit_book(book_id: int, data: BookRequest, services: Services) -> BookResponse:
    """Изменить только собственное доступное объявление."""
    return BookResponse.model_validate(services.book_service.edit(book_id, **data.model_dump()))


@router.delete("/books/{book_id}", response_model=MessageResponse, dependencies=write)
def delete_book(book_id: int, services: Services) -> MessageResponse:
    """Скрыть объявление и отменить ожидающие заявки."""
    services.book_service.delete(book_id, confirmed=True)
    return MessageResponse(message="Объявление удалено.")


@router.get("/exchanges", response_model=list[ExchangeViewResponse])
def exchanges(services: Services, incoming: bool = True) -> list[ExchangeViewResponse]:
    """Получить свои входящие или исходящие предложения."""
    return [
        ExchangeViewResponse.model_validate(view)
        for view in services.exchange_service.mine(incoming)
    ]


@router.get("/exchanges/{exchange_id}", response_model=ExchangeViewResponse)
def exchange_details(exchange_id: int, services: Services) -> ExchangeViewResponse:
    """Показать свою заявку и разрешённый контакт участника."""
    return ExchangeViewResponse.model_validate(services.exchange_service.view(exchange_id))


@router.post("/exchanges", response_model=ExchangeViewResponse, status_code=201, dependencies=write)
def send_exchange(data: ExchangeRequest, services: Services) -> ExchangeViewResponse:
    """Отправить предложение через сервис обменов."""
    item = services.exchange_service.send(data.requested_id, data.offered_id)
    return ExchangeViewResponse.model_validate(services.exchange_service.view(item.id))


@router.post(
    "/exchanges/{exchange_id}/{action}", response_model=ExchangeViewResponse, dependencies=write
)
def act(exchange_id: int, action: ExchangeAction, services: Services) -> ExchangeViewResponse:
    """Выполнить одну из четырёх команд обмена."""
    item = ExchangeCommand(services.exchange_service, action, exchange_id).execute()
    return ExchangeViewResponse.model_validate(services.exchange_service.view(item.id))
