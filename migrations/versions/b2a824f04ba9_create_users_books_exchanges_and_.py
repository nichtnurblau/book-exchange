"""create users books exchanges and confirmations

Revision ID: b2a824f04ba9
Revises:
Create Date: 2026-11-06 19:39:13.190962

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2a824f04ba9"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создать таблицы, внешние ключи, ограничения и индексы."""
    op.create_table(
        "users",
        sa.Column("login", sa.String(length=30), nullable=False),
        sa.Column("display_login", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("city", sa.String(length=80), nullable=False),
        sa.Column("contact", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.LargeBinary(), nullable=False),
        sa.Column("salt", sa.LargeBinary(), nullable=False),
        sa.CheckConstraint(
            "length(login) BETWEEN 3 AND 30 AND login = lower(login)", name=op.f("ck_users_login")
        ),
        sa.CheckConstraint("length(trim(city)) BETWEEN 1 AND 80", name=op.f("ck_users_city")),
        sa.CheckConstraint(
            "length(trim(contact)) BETWEEN 1 AND 100", name=op.f("ck_users_contact")
        ),
        sa.CheckConstraint("length(trim(name)) BETWEEN 1 AND 50", name=op.f("ck_users_name")),
        sa.PrimaryKeyConstraint("login", name=op.f("pk_users")),
    )
    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_login", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("author", sa.String(length=150), nullable=False),
        sa.Column("genre", sa.String(length=50), nullable=False),
        sa.Column("condition", sa.String(length=30), nullable=False),
        sa.Column("description", sa.String(length=1000), server_default="", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="Доступна", nullable=False),
        sa.Column("deleted", sa.Boolean(), server_default=sa.text("(false)"), nullable=False),
        sa.CheckConstraint(
            "condition IN ('Новое', 'Хорошее', 'Удовлетворительное')",
            name=op.f("ck_books_condition"),
        ),
        sa.CheckConstraint(
            "genre IN ('Художественная литература', 'Учебная литература', 'Научно-популярная литература', 'Другое')",
            name=op.f("ck_books_genre"),
        ),
        sa.CheckConstraint(
            "status IN ('Доступна', 'Зарезервирована', 'Обменена')", name=op.f("ck_books_status")
        ),
        sa.CheckConstraint("length(description) <= 1000", name=op.f("ck_books_description")),
        sa.CheckConstraint("length(trim(author)) BETWEEN 1 AND 150", name=op.f("ck_books_author")),
        sa.CheckConstraint("length(trim(title)) BETWEEN 1 AND 150", name=op.f("ck_books_title")),
        sa.ForeignKeyConstraint(
            ["owner_login"],
            ["users.login"],
            name=op.f("fk_books_owner_login_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_books")),
    )
    op.create_index(op.f("ix_books_owner_login"), "books", ["owner_login"], unique=False)
    op.create_table(
        "exchanges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("requested_id", sa.Integer(), nullable=False),
        sa.Column("offered_id", sa.Integer(), nullable=False),
        sa.Column("sender_login", sa.String(length=30), nullable=False),
        sa.Column("recipient_login", sa.String(length=30), nullable=False),
        sa.Column("pair_low", sa.Integer(), nullable=False),
        sa.Column("pair_high", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="Ожидает ответа", nullable=False),
        sa.CheckConstraint(
            "status IN ('Ожидает ответа', 'Принята', 'Отклонена', 'Отменена', 'Завершена')",
            name=op.f("ck_exchanges_status"),
        ),
        sa.CheckConstraint(
            "(pair_low = requested_id AND pair_high = offered_id AND requested_id < offered_id) OR (pair_low = offered_id AND pair_high = requested_id AND offered_id < requested_id)",
            name=op.f("ck_exchanges_canonical_pair"),
        ),
        sa.CheckConstraint("requested_id <> offered_id", name=op.f("ck_exchanges_different_books")),
        sa.CheckConstraint(
            "sender_login <> recipient_login", name=op.f("ck_exchanges_different_users")
        ),
        sa.ForeignKeyConstraint(
            ["offered_id"],
            ["books.id"],
            name=op.f("fk_exchanges_offered_id_books"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["recipient_login"],
            ["users.login"],
            name=op.f("fk_exchanges_recipient_login_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["requested_id"],
            ["books.id"],
            name=op.f("fk_exchanges_requested_id_books"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["sender_login"],
            ["users.login"],
            name=op.f("fk_exchanges_sender_login_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_exchanges")),
    )
    op.create_index(op.f("ix_exchanges_offered_id"), "exchanges", ["offered_id"], unique=False)
    op.create_index(op.f("ix_exchanges_requested_id"), "exchanges", ["requested_id"], unique=False)
    op.create_index(
        "uq_exchanges_active_pair",
        "exchanges",
        ["pair_low", "pair_high"],
        unique=True,
        postgresql_where=sa.text("status IN ('Ожидает ответа', 'Принята')"),
        sqlite_where=sa.text("status IN ('Ожидает ответа', 'Принята')"),
    )
    op.create_table(
        "exchange_confirmations",
        sa.Column("exchange_id", sa.Integer(), nullable=False),
        sa.Column("user_login", sa.String(length=30), nullable=False),
        sa.ForeignKeyConstraint(
            ["exchange_id"],
            ["exchanges.id"],
            name=op.f("fk_exchange_confirmations_exchange_id_exchanges"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_login"],
            ["users.login"],
            name=op.f("fk_exchange_confirmations_user_login_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "exchange_id", "user_login", name=op.f("pk_exchange_confirmations")
        ),
    )


def downgrade() -> None:
    """Удалить схему в порядке, обратном зависимостям."""
    op.drop_table("exchange_confirmations")
    op.drop_index(
        "uq_exchanges_active_pair",
        table_name="exchanges",
        postgresql_where=sa.text("status IN ('Ожидает ответа', 'Принята')"),
        sqlite_where=sa.text("status IN ('Ожидает ответа', 'Принята')"),
    )
    op.drop_index(op.f("ix_exchanges_requested_id"), table_name="exchanges")
    op.drop_index(op.f("ix_exchanges_offered_id"), table_name="exchanges")
    op.drop_table("exchanges")
    op.drop_index(op.f("ix_books_owner_login"), table_name="books")
    op.drop_table("books")
    op.drop_table("users")
