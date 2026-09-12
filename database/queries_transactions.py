"""Transaction-history query helpers for the profile page.

Pure data access: no Flask imports, raw sqlite3 only via get_db().
"""

from database.db import get_db


def get_recent_transactions(user_id, limit=10):
    """Return the user's most recent expenses as plain dicts, newest first.

    Ties on the same `date` are broken by `id DESC` so the order is stable
    across calls instead of depending on SQLite's unspecified tie order.
    `description` is nullable in the schema; it is normalised to "" here so
    templates never have to guard against None.
    """
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT date, description, category, amount FROM expenses "
            "WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    finally:
        conn.close()

    return [
        {
            "date": row["date"],
            "description": row["description"] if row["description"] is not None else "",
            "category": row["category"],
            "amount": float(row["amount"]),
        }
        for row in rows
    ]
