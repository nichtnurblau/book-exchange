from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class UserRecord(Base):
    """Учётная запись с нормализованным ключом и исходным написанием логина."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("length(login) BETWEEN 3 AND 30 AND login = lower(login)", name="login"),
        CheckConstraint("length(trim(name)) BETWEEN 1 AND 50", name="name"),
        CheckConstraint("length(trim(city)) BETWEEN 1 AND 80", name="city"),
        CheckConstraint("length(trim(contact)) BETWEEN 1 AND 100", name="contact"),
    )

    login: Mapped[str] = mapped_column(String(30), primary_key=True)
    display_login: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(50))
    city: Mapped[str] = mapped_column(String(80))
    contact: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[bytes] = mapped_column(LargeBinary)
    salt: Mapped[bytes] = mapped_column(LargeBinary)
    books: Mapped[list[BookRecord]] = relationship(back_populates="owner", passive_deletes="all")
    sent_exchanges: Mapped[list[ExchangeRecord]] = relationship(
        back_populates="sender", foreign_keys="ExchangeRecord.sender_login", passive_deletes="all"
    )
    received_exchanges: Mapped[list[ExchangeRecord]] = relationship(
        back_populates="recipient",
        foreign_keys="ExchangeRecord.recipient_login",
        passive_deletes="all",
    )
    confirmed_exchanges: Mapped[list[ExchangeRecord]] = relationship(
        secondary="exchange_confirmations", back_populates="confirmed_by", passive_deletes=True
    )


class BookRecord(Base):
    """Один экземпляр книги; удаление объявления выполняется логическим флагом."""

    __tablename__ = "books"
    __table_args__ = (
        CheckConstraint("length(trim(title)) BETWEEN 1 AND 150", name="title"),
        CheckConstraint("length(trim(author)) BETWEEN 1 AND 150", name="author"),
        CheckConstraint("length(description) <= 1000", name="description"),
        CheckConstraint(
            "genre IN ('Художественная литература', 'Учебная литература', 'Научно-популярная литература', 'Другое')",
            name="genre",
        ),
        CheckConstraint(
            "condition IN ('Новое', 'Хорошее', 'Удовлетворительное')", name="condition"
        ),
        CheckConstraint("status IN ('Доступна', 'Зарезервирована', 'Обменена')", name="status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_login: Mapped[str] = mapped_column(
        ForeignKey("users.login", ondelete="RESTRICT"), index=True
    )
    title: Mapped[str] = mapped_column(String(150))
    author: Mapped[str] = mapped_column(String(150))
    genre: Mapped[str] = mapped_column(String(50))
    condition: Mapped[str] = mapped_column(String(30))
    description: Mapped[str] = mapped_column(String(1000), default="", server_default="")
    status: Mapped[str] = mapped_column(String(32), default="Доступна", server_default="Доступна")
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    owner: Mapped[UserRecord] = relationship(back_populates="books")
    requested_exchanges: Mapped[list[ExchangeRecord]] = relationship(
        back_populates="requested",
        foreign_keys="ExchangeRecord.requested_id",
        passive_deletes="all",
    )
    offered_exchanges: Mapped[list[ExchangeRecord]] = relationship(
        back_populates="offered", foreign_keys="ExchangeRecord.offered_id", passive_deletes="all"
    )


class ExchangeRecord(Base):
    """Предложение обмена и двусторонние связи с участниками и книгами."""

    __tablename__ = "exchanges"
    __table_args__ = (
        CheckConstraint("requested_id <> offered_id", name="different_books"),
        CheckConstraint("sender_login <> recipient_login", name="different_users"),
        CheckConstraint(
            "status IN ('Ожидает ответа', 'Принята', 'Отклонена', 'Отменена', 'Завершена')",
            name="status",
        ),
        CheckConstraint(
            "(pair_low = requested_id AND pair_high = offered_id AND requested_id < offered_id) OR (pair_low = offered_id AND pair_high = requested_id AND offered_id < requested_id)",
            name="canonical_pair",
        ),
        Index(
            "uq_exchanges_active_pair",
            "pair_low",
            "pair_high",
            unique=True,
            postgresql_where=text("status IN ('Ожидает ответа', 'Принята')"),
            sqlite_where=text("status IN ('Ожидает ответа', 'Принята')"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    requested_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="RESTRICT"), index=True
    )
    offered_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="RESTRICT"), index=True)
    sender_login: Mapped[str] = mapped_column(ForeignKey("users.login", ondelete="RESTRICT"))
    recipient_login: Mapped[str] = mapped_column(ForeignKey("users.login", ondelete="RESTRICT"))
    pair_low: Mapped[int] = mapped_column()
    pair_high: Mapped[int] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(
        String(32), default="Ожидает ответа", server_default="Ожидает ответа"
    )
    sender: Mapped[UserRecord] = relationship(
        back_populates="sent_exchanges", foreign_keys=[sender_login]
    )
    recipient: Mapped[UserRecord] = relationship(
        back_populates="received_exchanges", foreign_keys=[recipient_login]
    )
    requested: Mapped[BookRecord] = relationship(
        back_populates="requested_exchanges", foreign_keys=[requested_id]
    )
    offered: Mapped[BookRecord] = relationship(
        back_populates="offered_exchanges", foreign_keys=[offered_id]
    )
    confirmed_by: Mapped[list[UserRecord]] = relationship(
        secondary="exchange_confirmations",
        back_populates="confirmed_exchanges",
        passive_deletes=True,
    )


class ExchangeConfirmation(Base):
    """Таблица связи M:N: участник подтверждает конкретный обмен один раз."""

    __tablename__ = "exchange_confirmations"

    exchange_id: Mapped[int] = mapped_column(
        ForeignKey("exchanges.id", ondelete="CASCADE"), primary_key=True
    )
    user_login: Mapped[str] = mapped_column(
        ForeignKey("users.login", ondelete="CASCADE"), primary_key=True
    )
