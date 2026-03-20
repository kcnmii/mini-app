#!/bin/sh
set -e

echo "Running Alembic migrations..."

# Check if alembic_version table exists (i.e., Alembic was used before)
ALEMBIC_EXISTS=$(uv run python -c "
from app.core.db import engine
from sqlalchemy import inspect
insp = inspect(engine)
print('yes' if 'alembic_version' in insp.get_table_names() else 'no')
" 2>/dev/null || echo "no")

if [ "$ALEMBIC_EXISTS" = "no" ]; then
    # Check if application tables already exist (pre-Alembic database)
    TABLES_EXIST=$(uv run python -c "
from app.core.db import engine
from sqlalchemy import inspect
insp = inspect(engine)
print('yes' if 'clients' in insp.get_table_names() else 'no')
" 2>/dev/null || echo "no")

    if [ "$TABLES_EXIST" = "yes" ]; then
        echo "Existing database detected. Stamping baseline..."
        uv run alembic stamp 0001_baseline
    fi
fi

# Now run any pending migrations
uv run alembic upgrade head

echo "Migrations complete. Starting server..."
exec "$@"
