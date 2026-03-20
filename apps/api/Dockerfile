# ── API Dockerfile ──
FROM python:3.12-slim AS base

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency definition
COPY pyproject.toml ./

# Install dependencies
RUN uv sync --no-dev

# Copy Alembic configuration and migrations
COPY alembic.ini ./
COPY alembic/ alembic/

# Copy application source
COPY src/ src/

# Copy entrypoint script
COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

# Create data directory
RUN mkdir -p /app/data

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
