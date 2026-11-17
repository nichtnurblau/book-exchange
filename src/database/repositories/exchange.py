from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.mappers import ExchangeMapper
from src.database.models import ExchangeRecord, UserRecord
from src.exchange_models import Exchange
from src.repositories.exchange import ExchangeRepository


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
