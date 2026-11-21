from dataclasses import dataclass
from enum import Enum

from src.models.exchange import Exchange
from src.services.exchange import ExchangeService


class ExchangeAction(str, Enum):
    """Доступные команды изменения заявки."""

    ACCEPT = "accept"
    REJECT = "reject"
    CANCEL = "cancel"
    CONFIRM = "confirm"


@dataclass
class ExchangeCommand:
    """Команда обмена, общая для HTTP API и HTML-форм."""

    service: ExchangeService
    action: ExchangeAction
    exchange_id: int

    def execute(self) -> Exchange:
        """Передать действие сервису, который проверяет права и статус заявки."""
        handlers = {
            ExchangeAction.ACCEPT: self.service.accept,
            ExchangeAction.REJECT: self.service.reject,
            ExchangeAction.CANCEL: self.service.cancel,
            ExchangeAction.CONFIRM: self.service.confirm,
        }
        return handlers[self.action](self.exchange_id)
