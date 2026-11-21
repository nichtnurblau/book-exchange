from dataclasses import dataclass, field


@dataclass(frozen=True)
class User:
    """Учётная запись; исходный пароль в объекте не хранится."""

    login: str
    name: str
    city: str
    contact: str = field(repr=False)
    password_hash: bytes = field(repr=False)
    salt: bytes = field(repr=False)
