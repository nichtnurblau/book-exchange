FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./
EXPOSE 8000
CMD ["uv", "run", "--no-sync", "python", "-m", "src.main"]
