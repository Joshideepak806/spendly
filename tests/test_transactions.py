"""Unit tests for database.queries_transactions.get_recent_transactions.

Uses a temporary on-disk SQLite file (never the real spendly.db) with
hand-inserted fixture rows, so assertions do not depend on today's date
or on the shared seed data.
"""

import pytest

from database.db import get_db, init_db
from database.queries_transactions import get_recent_transactions


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Point the data layer at a throwaway DB file and create the schema."""
    monkeypatch.setattr("database.db.DB_PATH", tmp_path / "test.db")
    init_db()
    return get_db


def insert_user(name="Test User", email="test@example.com"):
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, "hash"),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def insert_expense(user_id, amount, category, date, description):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, date, description),
        )
        conn.commit()
    finally:
        conn.close()


def test_user_with_expenses_returns_newest_first(db):
    user_id = insert_user()
    insert_expense(user_id, 10.0, "Food", "2026-01-01", "Breakfast")
    insert_expense(user_id, 20.0, "Transport", "2026-01-03", "Taxi")
    insert_expense(user_id, 30.0, "Bills", "2026-01-02", "Water bill")

    result = get_recent_transactions(user_id)

    assert [r["date"] for r in result] == ["2026-01-03", "2026-01-02", "2026-01-01"]
    for item in result:
        assert set(item.keys()) == {"date", "description", "category", "amount"}
        assert isinstance(item["amount"], float)


def test_same_day_rows_tie_broken_by_id_desc(db):
    user_id = insert_user()
    insert_expense(user_id, 1.0, "Food", "2026-01-01", "First")
    insert_expense(user_id, 2.0, "Food", "2026-01-01", "Second")
    insert_expense(user_id, 3.0, "Food", "2026-01-01", "Third")

    result = get_recent_transactions(user_id)

    assert [r["description"] for r in result] == ["Third", "Second", "First"]


def test_user_with_no_expenses_returns_empty_list(db):
    user_id = insert_user()

    assert get_recent_transactions(user_id) == []


def test_unknown_user_returns_empty_list(db):
    assert get_recent_transactions(999999) == []


def test_limit_is_respected(db):
    user_id = insert_user()
    for day in range(1, 6):
        insert_expense(user_id, 5.0, "Food", f"2026-01-0{day}", f"Item {day}")

    result = get_recent_transactions(user_id, limit=2)

    assert len(result) == 2
    assert result[0]["description"] == "Item 5"
    assert result[1]["description"] == "Item 4"


def test_null_description_becomes_empty_string(db):
    user_id = insert_user()
    insert_expense(user_id, 15.0, "Other", "2026-01-01", None)

    result = get_recent_transactions(user_id)

    assert len(result) == 1
    assert result[0]["description"] == ""


def test_amount_is_float(db):
    user_id = insert_user()
    insert_expense(user_id, 42, "Food", "2026-01-01", "Snack")

    result = get_recent_transactions(user_id)

    assert isinstance(result[0]["amount"], float)
    assert result[0]["amount"] == 42.0
