#!/bin/sh
set -e

# Skip migrations if running as the bot (not the API server)
if echo "$@" | grep -q "telegram_bot_runner"; then
    echo "Bot mode — skipping migrations."
    exec "$@"
fi

echo "Running Alembic migrations & self-healing missing legacy tables..."

# 1. Unconditionally create any newly added tables missing in legacy Prod DB.
# This prevents crashes if tables like 'bank_accounts' were added to models 
# but missed by Alembic because Prod was already stamped as baseline.
uv run python -c "from app.core.db import engine, Base; Base.metadata.create_all(engine)"

# 2. Check if alembic_version table exists (i.e., Alembic was used before)
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

# 3. Now run any pending migrations
uv run alembic upgrade head

echo "Migrations complete. Starting server..."
exec "$@"
