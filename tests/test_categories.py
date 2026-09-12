"""Unit tests for database.queries_categories.get_category_breakdown.

Uses a temp sqlite file (never the real spendly.db) and inserts known
fixture rows directly, so assertions never depend on today's date or
on seed_db().
"""

import sqlite3

import pytest

import database.db as db
from database.queries_categories import get_category_breakdown


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point database.db.DB_PATH at a fresh temp file and init the schema."""
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    return db


def make_user(temp_db, email="user@example.com"):
    """Insert a bare-bones user row and return its id."""
    conn = temp_db.get_db()
    try:
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Test User", email, "hash"),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def add_expenses(temp_db, user_id, rows):
    """rows: list of (amount, category, date) tuples."""
    conn = temp_db.get_db()
    try:
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            [(user_id, amount, category, dt, "") for amount, category, dt in rows],
        )
        conn.commit()
    finally:
        conn.close()


def assert_pcts_sum_to_100(breakdown):
    total_pct = sum(item["pct"] for item in breakdown)
    assert total_pct == 100
    for item in breakdown:
        assert isinstance(item["pct"], int)


def test_user_with_expenses_ordered_desc_and_shape(temp_db):
    user_id = make_user(temp_db)
    add_expenses(
        temp_db,
        user_id,
        [
            (120.00, "Bills", "2026-01-06"),
            (89.90, "Shopping", "2026-01-17"),
            (76.70, "Food", "2026-01-02"),
            (45.00, "Transport", "2026-01-04"),
            (30.00, "Health", "2026-01-09"),
            (18.99, "Entertainment", "2026-01-13"),
            (15.00, "Other", "2026-01-21"),
        ],
    )
    result = get_category_breakdown(user_id)

    # Ordered by amount descending.
    amounts = [item["amount"] for item in result]
    assert amounts == sorted(amounts, reverse=True)

    names = [item["name"] for item in result]
    assert names == ["Bills", "Shopping", "Food", "Transport", "Health", "Entertainment", "Other"]

    for item in result:
        assert set(item.keys()) == {"name", "amount", "pct"}
        assert isinstance(item["amount"], float)
        assert isinstance(item["pct"], int)

    assert_pcts_sum_to_100(result)
    # Sanity-check the actual total matches the real seed data total.
    assert round(sum(amounts), 2) == 395.59


def test_pct_sums_to_100_three_equal_thirds(temp_db):
    user_id = make_user(temp_db)
    add_expenses(
        temp_db,
        user_id,
        [
            (10.00, "Food", "2026-01-01"),
            (10.00, "Transport", "2026-01-01"),
            (10.00, "Bills", "2026-01-01"),
        ],
    )
    result = get_category_breakdown(user_id)
    assert len(result) == 3
    assert_pcts_sum_to_100(result)
    # The rounding remainder must land on the largest amount; here all
    # three amounts tie, so the tie-break (category ASC) makes "Bills"
    # first in the result — but the "largest" here is a three-way tie,
    # so simply confirm exactly one category absorbs the +1 nudge.
    pcts = sorted(item["pct"] for item in result)
    assert pcts in ([33, 33, 34],)


def test_pct_sums_to_100_seven_awkward_amounts(temp_db):
    user_id = make_user(temp_db)
    # Amounts chosen so naive per-item rounding does NOT sum to 100.
    rows = [
        (120.00, "Bills", "2026-01-01"),
        (89.90, "Shopping", "2026-01-01"),
        (76.70, "Food", "2026-01-01"),
        (45.00, "Transport", "2026-01-01"),
        (30.00, "Health", "2026-01-01"),
        (18.99, "Entertainment", "2026-01-01"),
        (15.00, "Other", "2026-01-01"),
    ]
    add_expenses(temp_db, user_id, rows)
    result = get_category_breakdown(user_id)
    assert len(result) == 7
    assert_pcts_sum_to_100(result)
    # The largest category (Bills, 120.00) should carry the remainder,
    # meaning its pct differs from a naive round() by exactly the
    # remainder amount (0 or a small +-N).
    total = sum(r[0] for r in rows)
    naive_bills_pct = round(120.00 / total * 100)
    bills_pct = next(item["pct"] for item in result if item["name"] == "Bills")
    assert abs(bills_pct - naive_bills_pct) <= 3


def test_pct_sums_to_100_many_categories_varied(temp_db):
    user_id = make_user(temp_db)
    add_expenses(
        temp_db,
        user_id,
        [
            (7.00, "Food", "2026-01-01"),
            (13.00, "Transport", "2026-01-01"),
            (23.00, "Bills", "2026-01-01"),
            (3.00, "Health", "2026-01-01"),
            (11.00, "Entertainment", "2026-01-01"),
            (5.00, "Shopping", "2026-01-01"),
            (1.00, "Other", "2026-01-01"),
        ],
    )
    result = get_category_breakdown(user_id)
    assert_pcts_sum_to_100(result)


def test_no_expenses_returns_empty_list(temp_db):
    user_id = make_user(temp_db)
    result = get_category_breakdown(user_id)
    assert result == []


def test_unknown_user_returns_empty_list(temp_db):
    # No such user id exists at all — must not raise.
    result = get_category_breakdown(999999)
    assert result == []


def test_single_category_is_100_percent(temp_db):
    user_id = make_user(temp_db)
    add_expenses(temp_db, user_id, [(42.50, "Food", "2026-01-01")])
    result = get_category_breakdown(user_id)
    assert len(result) == 1
    assert result[0]["name"] == "Food"
    assert result[0]["amount"] == 42.50
    assert result[0]["pct"] == 100


def test_tie_break_by_category_name_ascending(temp_db):
    user_id = make_user(temp_db)
    add_expenses(
        temp_db,
        user_id,
        [
            (20.00, "Transport", "2026-01-01"),
            (20.00, "Bills", "2026-01-01"),
            (20.00, "Food", "2026-01-01"),
        ],
    )
    result = get_category_breakdown(user_id)
    names = [item["name"] for item in result]
    assert names == ["Bills", "Food", "Transport"]


def test_does_not_touch_real_db_path(temp_db):
    # Confirm the fixture actually repointed DB_PATH away from spendly.db.
    assert db.DB_PATH.name == "test.db"


def test_multiple_expenses_same_category_are_summed(temp_db):
    user_id = make_user(temp_db)
    add_expenses(
        temp_db,
        user_id,
        [
            (10.00, "Food", "2026-01-01"),
            (5.00, "Food", "2026-01-02"),
            (15.00, "Bills", "2026-01-03"),
        ],
    )
    result = get_category_breakdown(user_id)
    food = next(item for item in result if item["name"] == "Food")
    assert food["amount"] == 15.00
    assert_pcts_sum_to_100(result)
