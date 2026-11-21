from dataclasses import dataclass
from enum import Enum

GENRES = (
    "Художественная литература",
    "Учебная литература",
    "Научно-популярная литература",
    "Другое",
)
CONDITIONS = ("Новое", "Хорошее", "Удовлетворительное")


class BookStatus(str, Enum):
    """Допустимые состояния физического экземпляра книги."""

    AVAILABLE = "Доступна"
    RESERVED = "Зарезервирована"
    EXCHANGED = "Обменена"


@dataclass(frozen=True)
class Book:
    """Объявление об одном экземпляре; удаление сохраняет запись для истории."""

    id: int
    owner_login: str
    title: str
    author: str
    genre: str
    condition: str
    description: str = ""
    status: BookStatus = BookStatus.AVAILABLE
    deleted: bool = False
