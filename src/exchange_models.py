from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ExchangeStatus(str, Enum):
    """Состояния заявки на обмен одной книги на другую."""

    WAITING = "Ожидает ответа"
    ACCEPTED = "Принята"
    REJECTED = "Отклонена"
    CANCELLED = "Отменена"
    COMPLETED = "Завершена"


@dataclass(frozen=True)
class Exchange:
    """Заявка с участниками и независимыми подтверждениями передачи."""

    id: int
    requested_id: int
    offered_id: int
    sender: str
    recipient: str
    created_at: datetime
    status: ExchangeStatus = ExchangeStatus.WAITING
    confirmations: frozenset[str] = field(default_factory=frozenset)

    @property
    def book_ids(self) -> frozenset[int]:
        """Вернуть пару книг независимо от направления предложения."""
        return frozenset((self.requested_id, self.offered_id))
