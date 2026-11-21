from pydantic import BaseModel, ConfigDict, Field


class RequestDTO(BaseModel):
    """Общие настройки входных данных."""

    model_config = ConfigDict(extra="forbid")


class RegistrationRequest(RequestDTO):
    """Поля регистрации пользователя."""

    login: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=8, max_length=128, repr=False)
    name: str = Field(min_length=1, max_length=50)
    city: str = Field(min_length=1, max_length=80)
    contact: str = Field(min_length=1, max_length=100)


class LoginRequest(RequestDTO):
    """Данные входа без отражения пароля в представлении объекта."""

    login: str
    password: str = Field(repr=False)


class BookRequest(RequestDTO):
    """Редактируемые поля объявления; владелец определяется сессией."""

    title: str = Field(min_length=1, max_length=150)
    author: str = Field(min_length=1, max_length=150)
    genre: str
    condition: str
    description: str = Field(default="", max_length=1000)


class ExchangeRequest(RequestDTO):
    """Предложение обменять две книги."""

    requested_id: int = Field(gt=0)
    offered_id: int = Field(gt=0)
