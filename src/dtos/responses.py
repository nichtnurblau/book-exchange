from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.models.book import BookStatus
from src.models.exchange import ExchangeStatus


class ResponseDTO(BaseModel):
    """Чтение данных из предметных dataclass."""

    model_config = ConfigDict(from_attributes=True)


class UserResponse(ResponseDTO):
    """Собственная учётная запись без хеша и соли."""

    login: str
    name: str
    city: str
    contact: str


class BookResponse(ResponseDTO):
    """Данные объявления."""

    id: int
    owner_login: str
    title: str
    author: str
    genre: str
    condition: str
    description: str
    status: BookStatus
    deleted: bool


class CardResponse(ResponseDTO):
    """Карточка каталога без контакта владельца."""

    book: BookResponse
    owner_name: str
    city: str


class ExchangeResponse(ResponseDTO):
    """Состояние заявки."""

    id: int
    requested_id: int
    offered_id: int
    sender: str
    recipient: str
    created_at: datetime
    status: ExchangeStatus
    confirmations: frozenset[str]


class ExchangeViewResponse(ResponseDTO):
    """Заявка с контактом, доступным только после принятия."""

    exchange: ExchangeResponse
    requested: BookResponse
    offered: BookResponse
    partner_name: str
    partner_contact: str | None


class MessageResponse(BaseModel):
    """Результат действия без данных сущности."""

    message: str


class SessionResponse(BaseModel):
    """Текущий пользователь и CSRF-токен для изменяющих запросов."""

    user: UserResponse | None
    csrf_token: str
