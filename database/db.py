"""SQLite data layer for Spendly.

Exposes three functions:
    get_db()   - open a connection with Row access and foreign keys enabled
    init_db()  - create tables (idempotent)
    seed_db()  - insert demo data once
"""

import sqlite3
from datetime import date
from pathlib import Path

from werkzeug.security import generate_password_hash

# <repo root>/expense_tracker.db, independent of the current working directory.
DB_PATH = Path(__file__).resolve().parent.parent / "expense_tracker.db"

CATEGORIES = [
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    created_at    TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    amount      REAL    NOT NULL,
    category    TEXT    NOT NULL,
    date        TEXT    NOT NULL,
    description TEXT,
    created_at  TEXT    DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""


def get_db():
    """Return a SQLite connection with dict-like rows and FK enforcement on."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables. Safe to call repeatedly."""
    conn = get_db()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def seed_db():
    """Insert one demo user and 8 sample expenses, only if the DB is empty."""
    conn = get_db()
    try:
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count > 0:
            return

        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
        )
        user_id = cur.lastrowid

        # Dates spread across the current month; days capped at 28 so the
        # seed never produces an invalid date in short months.
        today = date.today()

        def on_day(d):
            return today.replace(day=d).isoformat()

        expenses = [
            (user_id, 12.50,  "Food",          on_day(2),  "Lunch at cafe"),
            (user_id, 45.00,  "Transport",     on_day(4),  "Monthly metro pass"),
            (user_id, 120.00, "Bills",         on_day(6),  "Electricity bill"),
            (user_id, 30.00,  "Health",        on_day(9),  "Pharmacy"),
            (user_id, 18.99,  "Entertainment", on_day(13), "Movie ticket"),
            (user_id, 89.90,  "Shopping",      on_day(17), "New shoes"),
            (user_id, 15.00,  "Other",         on_day(21), "Gift wrapping"),
            (user_id, 64.20,  "Food",          on_day(26), "Weekly groceries"),
        ]
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            expenses,
        )
        conn.commit()
    finally:
        conn.close()
