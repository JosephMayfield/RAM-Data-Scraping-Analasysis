"""Create the SQLite database and tables if they don't already exist.

Safe to run repeatedly - CREATE TABLE IF NOT EXISTS won't touch existing data.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent / "schema.sql"
DB_PATH = Path(__file__).parent.parent / "data" / "ram_data.db"


def init_db(db_path: Path = DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    schema = SCHEMA_PATH.read_text()
    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema)


if __name__ == "__main__":
    init_db()
    print(f"Initialized database at {DB_PATH}")
