from __future__ import annotations

from enum import Enum


class MenuCommand(Enum):
    """Номера и названия пунктов главного меню."""

    EXIT = ("0", "Закрыть программу")
    REGISTER = ("1", "Регистрация")
    LOGIN = ("2", "Вход")
    ACCOUNT = ("3", "Моя учётная запись")
    LOGOUT = ("4", "Выйти из учётной записи")
    CATALOG = ("5", "Каталог")
    SEARCH = ("6", "Поиск и фильтры")
    BOOK_CARD = ("7", "Карточка книги")
    MY_BOOKS = ("8", "Мои книги")
    ADD_BOOK = ("9", "Добавить книгу")
    EDIT_BOOK = ("10", "Изменить книгу")
    DELETE_BOOK = ("11", "Удалить книгу")
    SEND_EXCHANGE = ("12", "Предложить обмен")
    MY_EXCHANGES = ("13", "Мои заявки")
    EXCHANGE_DETAILS = ("14", "Открыть заявку")
    ACCEPT_EXCHANGE = ("15", "Принять заявку")
    REJECT_EXCHANGE = ("16", "Отклонить заявку")
    CANCEL_EXCHANGE = ("17", "Отменить заявку")
    CONFIRM_EXCHANGE = ("18", "Подтвердить передачу")

    def __init__(self, code: str, title: str) -> None:
        """Сохранить номер и текст пункта меню."""
        self.code = code
        self.title = title

    @classmethod
    def from_code(cls, code: str) -> MenuCommand:
        """Найти команду по введённому номеру."""
        for command in cls:
            if command.code == code:
                return command
        raise ValueError("Выберите доступный пункт меню.")
