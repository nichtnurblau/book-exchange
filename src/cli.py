from getpass import getpass

from auth import AuthService


class ConsoleApp:
    """Показать консольный интерфейс первого этапа лабораторной №3."""

    def __init__(self, auth: AuthService) -> None:
        """Получить сервис, отвечающий за учётные записи."""
        self._auth = auth

    def run(self) -> None:
        """Обрабатывать команды до выхода, EOF или Ctrl+C."""
        print("Книгообмен — регистрация, вход и выход.")
        print("Данные существуют только до закрытия программы.")
        try:
            while True:
                user = self._auth.current_user
                print(f"\nТекущий пользователь: {user.name if user else 'Гость'}")
                if user is None:
                    print("1 — Регистрация\n2 — Вход\n0 — Закрыть программу")
                else:
                    print(
                        "3 — Моя учётная запись\n4 — Выйти из учётной записи\n0 — Закрыть программу"
                    )
                command = input("Выберите действие: ").strip()
                try:
                    if command == "0":
                        break
                    if command == "1" and user is None:
                        self._register()
                    elif command == "2" and user is None:
                        self._login()
                    elif command == "3":
                        self._show_account()
                    elif command == "4" and user is not None:
                        self._auth.logout()
                        print("Вы вышли из учётной записи.")
                    else:
                        print("Выберите доступный пункт меню.")
                except (ValueError, PermissionError) as error:
                    print(f"Ошибка: {error}")
        except (EOFError, KeyboardInterrupt):
            print("\nВвод завершён.")
        finally:
            self._auth.logout()
        print("Программа закрыта. Данные удалены из памяти.")

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
