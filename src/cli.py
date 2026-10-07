from collections.abc import Callable
from getpass import getpass

from auth import AuthService
from book_cli import BookConsole
from exchange_cli import ExchangeConsole


class ConsoleApp:
    """Показать консольный интерфейс лабораторной №3."""

    def __init__(self, auth: AuthService, books: BookConsole, exchanges: ExchangeConsole) -> None:
        """Получить сервис авторизации и консольные разделы."""
        self._auth = auth
        self._books = books
        self._exchanges = exchanges

    def _actions(self) -> dict[str, tuple[str, Callable[[], None]]]:
        """Сформировать доступное меню с учётом текущей сессии."""
        actions = {
            "5": ("Каталог", self._books.catalog),
            "6": ("Поиск и фильтры", self._books.search),
            "7": ("Карточка книги", self._books.card),
        }
        if self._auth.current_user is None:
            actions.update({"1": ("Регистрация", self._register), "2": ("Вход", self._login)})
        else:
            actions.update(
                {
                    "3": ("Моя учётная запись", self._show_account),
                    "4": ("Выйти из учётной записи", self._logout),
                    "8": ("Мои книги", self._books.mine),
                    "9": ("Добавить книгу", self._books.add),
                    "10": ("Изменить книгу", self._books.edit),
                    "11": ("Удалить книгу", self._books.delete),
                    "12": ("Предложить обмен", self._exchanges.send),
                    "13": ("Мои заявки", self._exchanges.list_requests),
                    "14": ("Открыть заявку", self._exchanges.details),
                    "15": ("Принять заявку", self._exchanges.accept),
                    "16": ("Отклонить заявку", self._exchanges.reject),
                    "17": ("Отменить заявку", self._exchanges.cancel),
                    "18": ("Подтвердить передачу", self._exchanges.confirm),
                }
            )
        return actions

    def run(self) -> None:
        """Обрабатывать команды до выхода, EOF или Ctrl+C."""
        print("Книгообмен — обмен бумажными книгами.")
        print("Данные существуют только до закрытия программы.")
        try:
            while True:
                user = self._auth.current_user
                print(f"\nТекущий пользователь: {user.name if user else 'Гость'}")
                actions = self._actions()
                for key in sorted(actions, key=int):
                    print(f"{key} — {actions[key][0]}")
                print("0 — Закрыть программу")
                command = input("Выберите действие: ").strip()
                if command == "0":
                    break
                try:
                    if command in actions:
                        actions[command][1]()
                    elif user is None and command in {
                        "3",
                        "4",
                        "8",
                        "9",
                        "10",
                        "11",
                        "12",
                        "13",
                        "14",
                        "15",
                        "16",
                        "17",
                        "18",
                    }:
                        self._auth.require_user()
                    else:
                        print("Выберите доступный пункт меню.")
                except (ValueError, PermissionError) as error:
                    print(f"Ошибка: {error}")
        except (EOFError, KeyboardInterrupt):
            print("\nВвод завершён.")
        finally:
            self._auth.logout()
        print("Программа закрыта. Данные удалены из памяти.")

    def _logout(self) -> None:
        """Завершить сессию, сохранив данные до закрытия программы."""
        self._auth.logout()
        print("Вы вышли из учётной записи.")

    def _register(self) -> None:
        """Запросить поля и передать их сервису регистрации."""
        login = input("Логин: ")
        password = getpass("Пароль (ввод скрыт): ")
        name = input("Имя: ")
        city = input("Город: ")
        contact = input("Контакт: ")
        user = self._auth.register(login, password, name, city, contact)
        print(f"Учётная запись {user.login} создана. Теперь выполните вход.")

    def _login(self) -> None:
        """Запросить логин и пароль и начать сессию."""
        login = input("Логин: ")
        password = getpass("Пароль (ввод скрыт): ")
        user = self._auth.login(login, password)
        print(f"Вход выполнен: {user.name}.")

    def _show_account(self) -> None:
        """Показать собственную запись как проверку доступа в рамках Ф2."""
        user = self._auth.require_user()
        print(f"Логин: {user.login}\nИмя: {user.name}\nГород: {user.city}")
