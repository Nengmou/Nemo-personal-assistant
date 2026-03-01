"""SQLite database connection and schema initialization."""

import os
import sqlite3

from nemo import config

_connection = None


def get_connection() -> sqlite3.Connection:
    """Get or create the SQLite connection."""
    global _connection
    if _connection is None:
        os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
        _connection = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        _connection.row_factory = sqlite3.Row
    return _connection


def init_db() -> None:
    """Create tables if they don't exist."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'work',
            priority TEXT NOT NULL DEFAULT 'medium',
            status TEXT NOT NULL DEFAULT 'pending',
            due_date TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            completed_at TEXT
        )
    """)
    conn.commit()
