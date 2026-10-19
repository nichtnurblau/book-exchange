class ConsoleInput:
    """Общие операции ввода для консольных разделов."""

    @staticmethod
    def read_id(prompt: str) -> int:
        """Прочитать положительный числовой ID с понятной ошибкой."""
        text = input(prompt).strip()
        try:
            value = int(text)
        except ValueError:
            raise ValueError("ID должен быть целым положительным числом.") from None
        if value <= 0:
            raise ValueError("ID должен быть целым положительным числом.")
        return value

    @staticmethod
    def choose(label: str, options: tuple[str, ...]) -> str:
        """Предложить выбор одного значения по номеру."""
        print(label)
        for number, option in enumerate(options, 1):
            print(f"{number} — {option}")
        index = ConsoleInput.read_id("Номер: ")
        if index > len(options):
            raise ValueError("Нет такого пункта в списке.")
        return options[index - 1]
