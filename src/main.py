from auth import AuthService
from cli import ConsoleApp
from repositories import InMemoryUserRepository
from security import PasswordHasher


def main() -> None:
    """Собрать компоненты и запустить консольное приложение."""
    repository = InMemoryUserRepository()
    auth = AuthService(repository, PasswordHasher())
    ConsoleApp(auth).run()


if __name__ == "__main__":
    main()
