from collections.abc import Callable
from contextlib import AbstractContextManager, nullcontext
from getpass import getpass

from src.book_cli import BookConsole
from src.exchange_cli import ExchangeConsole
from src.menu import MenuCommand
from src.services.user import UserService


class ConsoleApp:
    """Показать консольный интерфейс книгообмена."""

    def __init__(
        self,
        user_service: UserService,
        book_cli: BookConsole,
        exchange_cli: ExchangeConsole,
        transaction: Callable[[], AbstractContextManager[None]] = nullcontext,
        persistent: bool = False,
    ) -> None:
        """Получить сервис авторизации и консольные разделы."""
        self._user_service = user_service
        self._book_cli = book_cli
        self._exchange_cli = exchange_cli
        self._transaction = transaction
        self._persistent = persistent

    def run(self) -> None:
        """Обрабатывать команды до выхода, EOF или Ctrl+C."""
        print("Книгообмен — обмен бумажными книгами.")
        print(
            "Данные сохраняются в БД."
            if self._persistent
            else "Данные существуют только до закрытия программы."
        )
        try:
            while True:
                user = self._user_service.current_user
                print(f"\nТекущий пользователь: {user.name if user else 'Гость'}")
                actions = self._actions()
                for command in MenuCommand:
                    if command in actions:
                        print(f"{command.code} — {command.title}")
                print(f"{MenuCommand.EXIT.code} — {MenuCommand.EXIT.title}")
                try:
                    command = MenuCommand.from_code(input("Выберите действие: ").strip())
                    if command is MenuCommand.EXIT:
                        break
                    if command in actions:
                        with self._transaction():
                            actions[command]()
                    elif user is None:
                        self._user_service.require_user()
                    else:
                        print("Выберите доступный пункт меню.")
                except (ValueError, PermissionError) as error:
                    print(f"Ошибка: {error}")
        except (EOFError, KeyboardInterrupt):
            print("\nВвод завершён.")
        finally:
            self._user_service.logout()
        print(
            "Программа закрыта. Данные сохранены в БД."
            if self._persistent
            else "Программа закрыта. Данные удалены из памяти."
        )

    def _actions(self) -> dict[MenuCommand, Callable[[], None]]:
        """Сформировать доступное меню с учётом текущей сессии."""
        actions = {
            MenuCommand.CATALOG: self._book_cli.catalog,
            MenuCommand.SEARCH: self._book_cli.search,
            MenuCommand.BOOK_CARD: self._book_cli.card,
        }
        if self._user_service.current_user is None:
            actions.update({MenuCommand.REGISTER: self._register, MenuCommand.LOGIN: self._login})
        else:
            actions.update(
                {
                    MenuCommand.ACCOUNT: self._show_account,
                    MenuCommand.LOGOUT: self._logout,
                    MenuCommand.MY_BOOKS: self._book_cli.mine,
                    MenuCommand.ADD_BOOK: self._book_cli.add,
                    MenuCommand.EDIT_BOOK: self._book_cli.edit,
                    MenuCommand.DELETE_BOOK: self._book_cli.delete,
                    MenuCommand.SEND_EXCHANGE: self._exchange_cli.send,
                    MenuCommand.MY_EXCHANGES: self._exchange_cli.list_requests,
                    MenuCommand.EXCHANGE_DETAILS: self._exchange_cli.details,
                    MenuCommand.ACCEPT_EXCHANGE: self._exchange_cli.accept,
                    MenuCommand.REJECT_EXCHANGE: self._exchange_cli.reject,
                    MenuCommand.CANCEL_EXCHANGE: self._exchange_cli.cancel,
                    MenuCommand.CONFIRM_EXCHANGE: self._exchange_cli.confirm,
                }
            )
        return actions

    def _logout(self) -> None:
        """Завершить текущую пользовательскую сессию."""
        self._user_service.logout()
        print("Вы вышли из учётной записи.")

    def _register(self) -> None:
        """Запросить поля и передать их сервису регистрации."""
        login = self._read_registration_field(
            "Логин: ", self._user_service.validate_login, "Логин принят."
        )
        password = self._read_registration_field(
            "Пароль (ввод скрыт): ",
            self._user_service.validate_password,
            "Пароль принят.",
            hidden=True,
        )
        name = self._read_registration_field(
            "Имя: ", self._user_service.validate_name, "Имя принято."
        )
        city = self._read_registration_field(
            "Город: ", self._user_service.validate_city, "Город принят."
        )
        contact = self._read_registration_field(
            "Контакт: ", self._user_service.validate_contact, "Контакт принят."
        )
        user = self._user_service.register(login, password, name, city, contact)
        print(f"Учётная запись {user.login} создана. Теперь выполните вход.")

    def _login(self) -> None:
        """Запросить логин и пароль и начать сессию."""
        login = input("Логин: ")
        password = getpass("Пароль (ввод скрыт): ")
        user = self._user_service.login(login, password)
        print(f"Вход выполнен: {user.name}.")

    def _show_account(self) -> None:
        """Показать собственную запись как проверку доступа в рамках Ф2."""
        user = self._user_service.require_user()
        print(f"Логин: {user.login}\nИмя: {user.name}\nГород: {user.city}")

    def _read_registration_field(
        self, prompt: str, validate: Callable[[str], str], success: str, hidden: bool = False
    ) -> str:
        """Повторять ввод одного поля до успешной проверки."""
        while True:
            value = getpass(prompt) if hidden else input(prompt)
            try:
                value = validate(value)
            except ValueError as error:
                print(f"Ошибка: {error}")
                continue
            print(success)
            return value
