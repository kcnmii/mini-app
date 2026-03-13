from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.core.config import settings


def _database_path() -> Path:
    path = Path(settings.sqlite_path)
    if not path.is_absolute():
      path = Path.cwd() / path
    return path


def init_db() -> None:
    db_path = _database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                bin_iin TEXT DEFAULT '',
                contact_name TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS catalog_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                unit TEXT DEFAULT 'шт.',
                price REAL NOT NULL DEFAULT 0,
                sku TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                client_name TEXT NOT NULL,
                total_sum TEXT NOT NULL,
                total_sum_in_words TEXT NOT NULL,
                pdf_path TEXT NOT NULL,
                payload_json TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS document_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                quantity TEXT NOT NULL,
                unit TEXT NOT NULL,
                price TEXT NOT NULL,
                total TEXT NOT NULL,
                code TEXT DEFAULT '',
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS supplier_profile (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT DEFAULT '',
                company_iin TEXT DEFAULT '',
                company_iic TEXT DEFAULT '',
                company_bic TEXT DEFAULT '',
                company_kbe TEXT DEFAULT '',
                beneficiary_bank TEXT DEFAULT '',
                payment_code TEXT DEFAULT '',
                supplier_name TEXT DEFAULT '',
                supplier_iin TEXT DEFAULT '',
                supplier_address TEXT DEFAULT '',
                executor_name TEXT DEFAULT '',
                position TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                email TEXT DEFAULT '',
                logo_path TEXT DEFAULT '',
                signature_path TEXT DEFAULT '',
                stamp_path TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(_database_path())
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()
