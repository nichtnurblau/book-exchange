import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from src.console_input import ConsoleInput


class ConsoleInputTests(unittest.TestCase):
    """Проверки общих методов ввода, используемых обоими разделами."""

    def test_ids_and_choices(self) -> None:
        """Корректные числа принимаются, неподходящий ввод даёт ValueError."""
        with patch("builtins.input", return_value=" 12 "):
            self.assertEqual(ConsoleInput.read_id("ID: "), 12)
        for value in ("", "abc", "0", "-1", "1.5"):
            with self.subTest(value=value), patch("builtins.input", return_value=value):
                with self.assertRaises(ValueError):
                    ConsoleInput.read_id("ID: ")
        with redirect_stdout(io.StringIO()):
            with patch("builtins.input", return_value="2"):
                self.assertEqual(ConsoleInput.choose("Выбор", ("А", "Б")), "Б")
            with patch("builtins.input", return_value="3"):
                with self.assertRaises(ValueError):
                    ConsoleInput.choose("Выбор", ("А", "Б"))


if __name__ == "__main__":
    unittest.main()
