import hashlib
import hmac
import secrets


class PasswordHasher:
    """Хешировать пароли средствами стандартной библиотеки Python."""

    def hash_password(self, password: str, salt: bytes) -> bytes:
        """Вычислить PBKDF2-HMAC-SHA256 с индивидуальной солью."""
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600_000)

    def create(self, password: str) -> tuple[bytes, bytes]:
        """Вернуть новый хеш и случайную соль."""
        salt = secrets.token_bytes(16)
        return self.hash_password(password, salt), salt

    def verify(self, password: str, expected: bytes, salt: bytes) -> bool:
        """Сравнить вычисленный хеш с сохранённым."""
        return hmac.compare_digest(self.hash_password(password, salt), expected)
