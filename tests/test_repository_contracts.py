import unittest
from abc import ABC

from src.models import User
from src.repositories.book import BookRepository, InMemoryBookRepository
from src.repositories.exchange import ExchangeRepository, InMemoryExchangeRepository
from src.repositories.user import InMemoryUserRepository, UserRepository


class RepositoryContractTests(unittest.TestCase):
    """Проверить обязательность реализации методов абстрактных хранилищ."""

    def test_abstract_and_concrete_repositories(self) -> None:
        """Базовые хранилища не создаются, а InMemory реализуют их договор."""
        pairs = [
            (UserRepository, InMemoryUserRepository),
            (BookRepository, InMemoryBookRepository),
            (ExchangeRepository, InMemoryExchangeRepository),
        ]
        for abstract, concrete in pairs:
            with self.subTest(repository=abstract.__name__):
                self.assertTrue(issubclass(abstract, ABC))
                with self.assertRaises(TypeError):
                    abstract()
                self.assertIsInstance(concrete(), abstract)

    def test_missing_method_keeps_repository_abstract(self) -> None:
        """Наследник без поиска пользователя остаётся абстрактным."""

        class IncompleteUserRepository(UserRepository):
            """Неполная реализация для проверки ограничений ABC."""

            def add(self, user: User) -> None:
                """Предоставить один метод без реализации второго."""
                return None

        with self.assertRaises(TypeError):
            IncompleteUserRepository()


if __name__ == "__main__":
    unittest.main()
