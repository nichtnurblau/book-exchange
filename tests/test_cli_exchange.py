import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from main import main


class CliExchangeTests(unittest.TestCase):
    """Пройти полный пользовательский сценарий через настоящую точку входа."""

    def run_commands(self, commands: list[str], passwords: list[str]) -> str:
        """Подать ответы вместо клавиатуры и собрать консольный вывод."""
        output = io.StringIO()
        with (
            patch("builtins.input", side_effect=commands),
            patch("cli.getpass", side_effect=passwords),
            redirect_stdout(output),
        ):
            main()
        return output.getvalue()

    def test_two_users_complete_exchange(self) -> None:
        """Зарегистрировать двух читателей, добавить книги и завершить обмен."""
        commands = [
            "5",
            "9",
            "1",
            "anna",
            "Анна",
            "Волгоград",
            "anna@example.test",
            "2",
            "anna",
            "9",
            "Белый клык",
            "Джек Лондон",
            "1",
            "2",
            "",
            "4",
            "1",
            "boris",
            "Борис",
            "Волгоград",
            "boris@example.test",
            "2",
            "boris",
            "9",
            "Алгебра",
            "Иван Петров",
            "2",
            "1",
            "Учебник",
            "6",
            "БЕЛЫЙ",
            "2",
            "волгоград",
            "7",
            "1",
            "12",
            "1",
            "2",
            "13",
            "14",
            "1",
            "4",
            "2",
            "anna",
            "13",
            "15",
            "1",
            "14",
            "1",
            "18",
            "1",
            "4",
            "2",
            "boris",
            "18",
            "1",
            "8",
            "5",
            "0",
        ]
        output = self.run_commands(commands, ["testpass123"] * 6)
        self.assertIn("Книги не найдены.", output)
        self.assertIn("Сначала войдите", output)
        self.assertIn("Книга добавлена. ID: 1", output)
        self.assertIn("Книга добавлена. ID: 2", output)
        self.assertIn("Заявка создана. ID: 1", output)
        self.assertIn("Контакт для связи: boris@example.test", output)
        self.assertIn("Ожидается второй участник", output)
        self.assertIn("Обмен завершён", output)
        self.assertNotIn("testpass123", output)
        self.assertNotIn("Traceback", output)
        restarted = self.run_commands(["2", "anna", "5", "0"], ["testpass123"])
        self.assertIn("Неверный логин или пароль", restarted)
        self.assertIn("Книги не найдены", restarted)

    def test_edit_delete_bad_id_and_bad_choice(self) -> None:
        """Ошибочный ввод обрабатывается, удаление требует явного согласия."""
        commands = [
            "7",
            "abc",
            "7",
            "0",
            "1",
            "anna",
            "Анна",
            "Волгоград",
            "anna@example.test",
            "2",
            "anna",
            "9",
            "Книга",
            "Автор",
            "99",
            "9",
            "Книга",
            "Автор",
            "4",
            "1",
            "",
            "10",
            "1",
            "Новое название",
            "Другой автор",
            "2",
            "2",
            "Описание",
            "11",
            "1",
            "нет",
            "8",
            "11",
            "1",
            "да",
            "8",
            "0",
        ]
        output = self.run_commands(commands, ["testpass123", "testpass123"])
        self.assertIn("ID должен быть целым положительным числом", output)
        self.assertIn("Нет такого пункта", output)
        self.assertIn("Объявление изменено", output)
        self.assertIn("Удаление отменено", output)
        self.assertIn("Объявление удалено", output)
        self.assertIn("У вас пока нет книг", output)
        self.assertNotIn("Traceback", output)


if __name__ == "__main__":
    unittest.main()
