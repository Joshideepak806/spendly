"""Tests for database/queries_summary.py and the GET /profile route.

Every test repoints the data layer at a throwaway SQLite file (via the
`temp_db` fixture) before touching it, so the real `spendly.db` is never
read or written by this suite.
"""

from datetime import date

import pytest
from werkzeug.security import generate_password_hash

import app as flask_app_module
from database.db import get_db, init_db, seed_db
from database.queries_summary import get_summary_stats, get_user_by_id

# True seeded total for the demo user (Bills 120.00, Shopping 89.90,
# Food 12.50 + 64.20 = 76.70, Transport 45.00, Health 30.00,
# Entertainment 18.99, Other 15.00) = 395.59. The spec text says 346.24;
# that figure is wrong and must not be used.
SEED_TOTAL = 395.59
SEED_COUNT = 8
SEED_TOP_CATEGORY = "Bills"


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point database.db.DB_PATH at a fresh temp file and seed it."""
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("database.db.DB_PATH", db_path)
    init_db()
    seed_db()
    return db_path


@pytest.fixture
def client(temp_db):
    flask_app_module.app.config.update(TESTING=True, SECRET_KEY="test")
    with flask_app_module.app.test_client() as test_client:
        yield test_client


def login(test_client, email="demo@spendly.com", password="demo123"):
    return test_client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )


def insert_bare_user(name, email):
    """Insert a user with no expenses directly, return the new id."""
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash("irrelevant-pw")),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


# ------------------------------------------------------------------ #
# get_user_by_id                                                      #
# ------------------------------------------------------------------ #

def test_get_user_by_id_valid(temp_db):
    user = get_user_by_id(1)
    assert user["name"] == "Demo User"
    assert user["email"] == "demo@spendly.com"
    assert user["member_since"] == date.today().strftime("%B %Y")


def test_get_user_by_id_missing(temp_db):
    assert get_user_by_id(999999) is None


def test_get_user_by_id_never_leaks_password_hash(temp_db):
    user = get_user_by_id(1)
    assert "password_hash" not in user


# ------------------------------------------------------------------ #
# get_summary_stats                                                   #
# ------------------------------------------------------------------ #

def test_get_summary_stats_with_expenses(temp_db):
    stats = get_summary_stats(1)
    assert stats["total_spent"] == pytest.approx(SEED_TOTAL)
    assert stats["transaction_count"] == SEED_COUNT
    assert stats["top_category"] == SEED_TOP_CATEGORY
    # Seed expenses are dated within the current month.
    assert stats["month_spent"] == pytest.approx(SEED_TOTAL)
    assert "password_hash" not in stats


def test_get_summary_stats_no_expenses(temp_db):
    new_id = insert_bare_user("No Expenses", "noexpenses@example.com")
    stats = get_summary_stats(new_id)
    assert stats == {
        "total_spent": 0,
        "month_spent": 0,
        "transaction_count": 0,
        "top_category": "—",
    }


# ------------------------------------------------------------------ #
# GET /profile route                                                  #
# ------------------------------------------------------------------ #

def test_profile_unauthenticated_redirects_to_login(client):
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_profile_authenticated_shows_user_info(client):
    login(client)
    resp = client.get("/profile")
    body = resp.get_data(as_text=True)

    assert resp.status_code == 200
    assert "Demo User" in body
    assert "demo@spendly.com" in body
    assert "₹" in body  # the rupee symbol


def test_profile_authenticated_shows_correct_stats(client):
    login(client)
    resp = client.get("/profile")
    body = resp.get_data(as_text=True)

    assert "₹395.59" in body
    assert '<span class="stat-value">8</span>' in body
    assert '<span class="stat-value">Bills</span>' in body


def test_profile_never_leaks_password_hash(client):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE email = ?",
            ("demo@spendly.com",),
        ).fetchone()
    finally:
        conn.close()

    login(client)
    resp = client.get("/profile")
    body = resp.get_data(as_text=True)

    assert "password_hash" not in body
    assert row["password_hash"] not in body
