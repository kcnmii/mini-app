#!/bin/sh
set -e

echo "Running Alembic migrations..."

# On a FRESH database, tables already exist (from create_all in previous releases).
# Stamp the baseline so Alembic doesn't try to recreate them.
# On subsequent deploys, 'upgrade head' will only apply NEW migrations.
uv run alembic upgrade head 2>&1 || {
    echo "Migration failed, attempting to stamp baseline for existing DB..."
    uv run alembic stamp 0001_baseline
    uv run alembic upgrade head
}

echo "Migrations complete. Starting server..."
exec "$@"
