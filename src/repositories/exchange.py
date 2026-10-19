from abc import ABC, abstractmethod
from dataclasses import replace

from src.exchange_models import Exchange


class ExchangeRepository(ABC):
    """Договор хранения заявок и их истории."""

    @abstractmethod
    def add(self, exchange: Exchange) -> Exchange:
        """Назначить ID и сохранить новую заявку."""
        ...

    @abstractmethod
    def get(self, exchange_id: int) -> Exchange:
        """Найти заявку либо вызвать ValueError."""
        ...

    @abstractmethod
    def all(self) -> list[Exchange]:
        """Вернуть все заявки для отбора в сервисе."""
        ...

    @abstractmethod
    def save(self, exchange: Exchange) -> None:
        """Обновить существующую заявку."""
        ...


class InMemoryExchangeRepository(ExchangeRepository):
    """Хранить заявки до завершения процесса."""

    def __init__(self) -> None:
        """Создать пустое хранилище и счётчик."""
        self._items: dict[int, Exchange] = {}
        self._next_id = 1

    def add(self, exchange: Exchange) -> Exchange:
        """Сохранить заявку с автоматически выданным ID."""
        saved = replace(exchange, id=self._next_id)
        self._items[saved.id] = saved
        self._next_id += 1
        return saved

    def get(self, exchange_id: int) -> Exchange:
        """Получить заявку по ID."""
        if exchange_id not in self._items:
            raise ValueError("Заявка с таким ID не найдена.")
        return self._items[exchange_id]

    def all(self) -> list[Exchange]:
        """Вернуть новый список неизменяемых заявок."""
        return list(self._items.values())

    def save(self, exchange: Exchange) -> None:
        """Обновить ранее созданную заявку."""
        self.get(exchange.id)
        self._items[exchange.id] = exchange
