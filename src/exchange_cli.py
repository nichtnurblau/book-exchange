from book_cli import read_id
from exchange_models import ExchangeStatus
from exchanges import ExchangeService, ExchangeView


class ExchangeConsole:
    """Консольный интерфейс заявок текущего пользователя."""

    def __init__(self, service: ExchangeService) -> None:
        """Получить сервис обменов."""
        self._service = service

    def send(self) -> None:
        """Запросить чужую и собственную книгу для нового предложения."""
        requested = read_id("ID чужой книги, которую хотите получить: ")
        offered = read_id("ID своей книги, которую предлагаете: ")
        item = self._service.send(requested, offered)
        print(f"Заявка создана. ID: {item.id}. Статус: {item.status.value}.")

    def _print(self, view: ExchangeView) -> None:
        """Показать обе книги, участника, дату, статус и разрешённый контакт."""
        item = view.exchange
        date = item.created_at.astimezone().strftime("%d.%m.%Y %H:%M:%S %z")
        print(f"Заявка {item.id} от {date}: {item.status.value}")
        print(
            f"Запрошена: ID {view.requested.id}, {view.requested.title} — {view.requested.author}"
        )
        print(f"Предложена: ID {view.offered.id}, {view.offered.title} — {view.offered.author}")
        print(f"Другой участник: {view.partner_name}")
        print(f"Подтверждений передачи: {len(item.confirmations)}/2")
        if view.partner_contact is not None:
            print(f"Контакт для связи: {view.partner_contact}")

    def list_requests(self) -> None:
        """Показать отдельно входящие и исходящие заявки."""
        for incoming, title in [(True, "Входящие"), (False, "Исходящие")]:
            print(f"\n{title}:")
            items = self._service.mine(incoming)
            if not items:
                print("Заявок нет.")
            for view in items:
                self._print(view)

    def details(self) -> None:
        """Открыть одну свою заявку по ID."""
        self._print(self._service.view(read_id("ID заявки: ")))

    def accept(self) -> None:
        """Принять ожидающее предложение."""
        self._service.accept(read_id("ID входящей заявки: "))
        print("Заявка принята. Обе книги зарезервированы. Контакт доступен в заявке.")

    def reject(self) -> None:
        """Отклонить ожидающее предложение."""
        self._service.reject(read_id("ID входящей заявки: "))
        print("Заявка отклонена.")

    def cancel(self) -> None:
        """Отменить заявку по правилам доступа."""
        self._service.cancel(read_id("ID заявки: "))
        print("Заявка отменена. Резерв снят, если обмен был принят.")

    def confirm(self) -> None:
        """Подтвердить передачу книги от текущего участника."""
        item = self._service.confirm(read_id("ID принятой заявки: "))
        if item.status == ExchangeStatus.COMPLETED:
            print("Обмен завершён. Обе книги получили статус «Обменена».")
        else:
            print("Ваше подтверждение сохранено. Ожидается второй участник.")
