# Работа с базой данных

## Быстрый запуск с SQLite

Нужны Python 3.11+ и uv. Команды выполняются из корня репозитория:

```bash
uv sync
uv run alembic upgrade head
uv run python -m src.main
```

Если переменная `DATABASE_URL` не задана, используется `sqlite:///book_exchange.db`.
Файл создаётся миграцией Alembic и исключён из Git. Повторный `upgrade head`
без новых ревизий ничего не меняет. Приложение проверяет версию схемы перед меню
и не создаёт таблицы самостоятельно.

## PostgreSQL

Установите Docker Desktop с Compose и запустите его. В корне проекта:

```bash
uv sync
cp .env.example .env
docker compose up -d --wait
uv run --env-file .env alembic upgrade head
uv run --env-file .env alembic check
uv run --env-file .env python -m src.main
```

Compose читает `.env` автоматически; uv получает его через `--env-file`.
Пример рассчитан на локальную учебную БД. Если порт 5432 занят, измените
`POSTGRES_PORT` и порт в `DATABASE_URL` в `.env` на одно значение.
Для уже существующей внешней БД достаточно указать её URL с драйвером
`postgresql+psycopg` и выполнить миграции, запускать Compose не нужно.

Проверить таблицы и остановить контейнер:

```bash
docker compose exec db psql -U bookexchange -d bookexchange -c '\dt'
docker compose down
```

Именованный том `postgres_data` сохраняет данные после `down`. Не добавляйте `-v`,
если данные нужны. Настоящий `.env` с паролями не включается в Git.

## Миграции

Схема описана в [ER-диаграмме](er.md). Ограничения из неё перенесены в ORM-модели
и начальную миграцию. В проекте один `Base` и один набор `metadata`.
В `migrations/env.py` импортируются все четыре mapped-класса.

Alembic уже инициализирован, начальная ревизия включена в репозиторий.
При обычном запуске повторять `alembic init` и создавать новую начальную ревизию
не нужно. Начальная ревизия получена командой
`uv run alembic revision --autogenerate -m "create users books exchanges and confirmations"`
и проверена вручную. Таблицы создаются только через `upgrade`.

После следующего изменения схемы:

```bash
uv run --env-file .env alembic revision --autogenerate -m "describe schema change"
# Просмотрите upgrade и downgrade в созданной ревизии.
uv run --env-file .env alembic upgrade head
uv run --env-file .env alembic check
```

`alembic check` сравнивает текущую БД с ORM-моделями. Откат начальной ревизии
`alembic downgrade base` удаляет все таблицы приложения: применяйте его только
к отдельной тестовой БД. Тесты проверяют такой откат и повторное обновление.
Перед миграцией рабочей БД сделайте резервную копию.

## Код и транзакции

- `src/database/models.py`: `Mapped`, `mapped_column`, PK, FK, проверки и связи.
- `src/database/mappers.py`: преобразования между ORM-записями и прежними dataclass.
- `src/repositories/sqlalchemy/`: реализация прежних абстрактных репозиториев.
- `src/database/session.py`: общая `Session` и граница транзакции.
- `src/main.py`: сборка сервисов с SQL-репозиториями.

Сервисы продолжают работать с `User`, `Book` и `Exchange`. Mapper-классы читают
ORM-связи в открытой сессии и возвращают независимые неизменяемые dataclass.
ID книги и заявки выдаёт БД после `flush()`, вручную они не вычисляются.
В `users.login` хранится нормализованный ключ, в `display_login` — исходное
написание. Пароль сохраняется как хеш с солью, открытого пароля в таблице нет.

Каждая команда меню выполняется в одной транзакции. Репозитории вызывают
`flush()`, чтобы получить ID и проверить ограничения, а `Database.transaction()`
выполняет общее сохранение либо откат. Это сохраняет согласованность заявки,
резервирования обеих книг и отклонения конкурирующих предложений.
В PostgreSQL используется уровень `SERIALIZABLE`: при конфликте параллельных
операций транзакция откатывается и пользователь получает предложение повторить
команду. Автоматический повтор ввода не выполняется.

Удаление объявления остаётся логическим (`books.deleted`), чтобы не терять
историю. FK от книг и заявок используют `RESTRICT`. ORM не каскадирует удаление
с пользователя на книги и заявки. Для основной сущности остаётся стандартный
каскад `save-update, merge`, а `passive_deletes` передаёт проверку удаления БД.
Только строки связи `exchange_confirmations` имеют `ON DELETE CASCADE`:
удаление заявки удаляет её подтверждения, но не пользователей и книги.

## Проверка

```bash
uv run python -m unittest discover -s tests -v
uv run ruff check .
uv run ruff format --check .
uv run --env-file .env alembic check
```

Модульные тесты используют InMemory-репозитории; интеграционные повторяют правила
обмена с SQLAlchemy и проверяют перезапуск, FK, M:N, каскады и атомарный откат.
Каждая тестовая SQLite-БД создаётся миграцией Alembic.
GitHub Actions запускает PostgreSQL 16, проверяет миграцию, тесты и старт консоли.
Шесть проверок сохранения, ограничений, связей и отката повторяются на PostgreSQL.

Чтобы выполнить их локально после запуска Compose:

```bash
TEST_POSTGRES_URL=postgresql+psycopg://bookexchange:bookexchange@localhost:5432/bookexchange uv run python -m unittest tests.test_postgres -v
```

Тестовому пользователю нужно право `CREATE` на базу. Каждый тест создаёт схему
с уникальным именем `test_<uuid>`, применяет миграции в ней и удаляет только эту
схему после проверки. Таблицы основной схемы не затрагиваются.
Без `TEST_POSTGRES_URL` эти шесть тестов пропускаются; остальные выполняются
на SQLite и в памяти.

[Описание задания и подхода к миграциям](https://gist.github.com/Tamerlan91011/8c9f81979009bbffe1f3ce8b7e92fad6)
