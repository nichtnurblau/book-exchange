from book_models import CONDITIONS, GENRES, Book
from books import BookService
from catalog import CatalogService


def read_id(prompt: str) -> int:
    """Прочитать положительный числовой ID без вывода traceback."""
    text = input(prompt).strip()
    try:
        value = int(text)
    except ValueError:
        raise ValueError("ID должен быть целым положительным числом.") from None
    if value <= 0:
        raise ValueError("ID должен быть целым положительным числом.")
    return value


def choose(label: str, options: tuple[str, ...]) -> str:
    """Предложить выбор значения по номеру."""
    print(label)
    for number, option in enumerate(options, 1):
        print(f"{number} — {option}")
    index = read_id("Номер: ")
    if index > len(options):
        raise ValueError("Нет такого пункта в списке.")
    return options[index - 1]


class BookConsole:
    """Консольные операции с книгами без собственной бизнес-логики."""

    def __init__(self, books: BookService, catalog: CatalogService) -> None:
        """Получить сервисы собственных книг и публичного каталога."""
        self._books = books
        self._catalog = catalog

    def _print_book(self, book: Book) -> None:
        """Вывести основные поля одной книги."""
        print(f"ID {book.id}: {book.title} — {book.author}")
        print(f"Жанр: {book.genre}; состояние: {book.condition}; статус: {book.status.value}")
        print(f"Описание: {book.description or 'не указано'}")

    def catalog(self) -> None:
        """Показать все доступные объявления."""
        self._show_results("", "", "")

    def search(self) -> None:
        """Запросить поисковую строку и два совместных фильтра."""
        query = input("Часть названия или автора (Enter — все): ")
        genre = choose("Жанр", ("Все жанры",) + GENRES)
        city = input("Город (Enter — любой): ")
        self._show_results(query, "" if genre == "Все жанры" else genre, city)

    def _show_results(self, query: str, genre: str, city: str) -> None:
        """Отобразить результаты без контактов владельцев."""
        cards = self._catalog.search(query, genre, city)
        if not cards:
            print("Книги не найдены.")
        for card in cards:
            self._print_book(card.book)
            print(f"Владелец: {card.owner_name}; город: {card.city}\n")

    def card(self) -> None:
        """Открыть публичную карточку по ID."""
        card = self._catalog.get_card(read_id("ID книги: "))
        self._print_book(card.book)
        print(f"Владелец: {card.owner_name}; город: {card.city}")

    def mine(self) -> None:
        """Показать собственные объявления и их статусы."""
        books = self._books.mine()
        if not books:
            print("У вас пока нет книг.")
        for book in books:
            self._print_book(book)

    def _fields(self) -> tuple[str, str, str, str, str]:
        """Прочитать текстовые поля и значения из разрешённых списков."""
        title = input("Название: ")
        author = input("Автор: ")
        genre = choose("Жанр", GENRES)
        condition = choose("Состояние", CONDITIONS)
        description = input("Описание (можно оставить пустым): ")
        return title, author, genre, condition, description

    def add(self) -> None:
        """Создать объявление через сервис."""
        book = self._books.add(*self._fields())
        print(f"Книга добавлена. ID: {book.id}.")

    def edit(self) -> None:
        """После проверки прав заменить поля объявления."""
        book_id = read_id("ID своей книги: ")
        self._print_book(self._books.editable(book_id))
        print("Введите новые значения всех полей.")
        self._books.edit(book_id, *self._fields())
        print("Объявление изменено.")

    def delete(self) -> None:
        """Удалить объявление только после явного подтверждения."""
        book_id = read_id("ID своей книги: ")
        book = self._books.editable(book_id)
        confirmed = input(f"Удалить «{book.title}»? Напишите да: ").strip().casefold() == "да"
        if self._books.delete(book_id, confirmed):
            print("Объявление удалено. Ожидающие заявки на эту книгу отменены.")
        else:
            print("Удаление отменено.")
