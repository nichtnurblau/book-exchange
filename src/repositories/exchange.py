from abc import ABC, abstractmethod
from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.mappers import ExchangeMapper
from src.database.models import ExchangeRecord, UserRecord
from src.models.exchange import Exchange


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


class SQLAlchemyExchangeRepository(ExchangeRepository):
    """Хранить заявки и связи подтверждений в одной сессии."""

    def __init__(self, session: Session) -> None:
        """Получить сессию транзакции приложения."""
        self._session = session

    def add(self, exchange: Exchange) -> Exchange:
        """Создать заявку и получить ID, не выполняя commit."""
        record = ExchangeMapper.to_record(exchange, self._confirmations(exchange))
        self._session.add(record)
        self._session.flush()
        return ExchangeMapper.to_domain(record)

    def get(self, exchange_id: int) -> Exchange:
        """Найти заявку вместе с данными участников."""
        record = self._session.get(ExchangeRecord, exchange_id)
        if record is None:
            raise ValueError("Заявка с таким ID не найдена.")
        return ExchangeMapper.to_domain(record)

    def all(self) -> list[Exchange]:
        """Вернуть заявки в порядке ID."""
        return [
            ExchangeMapper.to_domain(record)
            for record in self._session.scalars(select(ExchangeRecord).order_by(ExchangeRecord.id))
        ]

    def save(self, exchange: Exchange) -> None:
        """Обновить заявку и набор подтвердивших участников."""
        record = self._session.get(ExchangeRecord, exchange.id)
        if record is None:
            raise ValueError("Заявка с таким ID не найдена.")
        ExchangeMapper.update_record(exchange, record, self._confirmations(exchange))
        self._session.flush()

    def _confirmations(self, exchange: Exchange) -> list[UserRecord]:
        """Преобразовать логины подтверждений в существующие записи участников."""
        result = []
        for login in sorted(exchange.confirmations):
            if login not in (exchange.sender, exchange.recipient):
                raise ValueError("Подтвердить обмен может только его участник.")
            record = self._session.get(UserRecord, login.casefold())
            if record is None:
                raise ValueError("Участник подтверждения не найден.")
            result.append(record)
        return result
