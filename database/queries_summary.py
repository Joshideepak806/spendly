"""Summary-stat query helpers for the profile page.

Exposes two functions, both pure data access (no Flask imports, no
`session` access — callers pass the `user_id` explicitly):
    get_user_by_id(user_id)   - name/email/member_since for one user
    get_summary_stats(user_id) - total/month spend, count, top category
"""

from datetime import date

from database.db import get_db


def get_user_by_id(user_id):
    """Return {"name", "email", "member_since"} for `user_id`, or None.

    `member_since` is derived from `users.created_at` (stored as
    "YYYY-MM-DD HH:MM:SS") and formatted as "Month YYYY". Never selects
    `password_hash`.
    """
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return None

    member_since = date.fromisoformat(row["created_at"][:10]).strftime("%B %Y")
    return {
        "name": row["name"],
        "email": row["email"],
        "member_since": member_since,
    }


def get_summary_stats(user_id):
    """Return {"total_spent", "month_spent", "transaction_count", "top_category"}.

    `total_spent` and `month_spent` are floats (SQL NULL coalesced to 0).
    `top_category` is the category with the highest summed amount, ties
    broken alphabetically; "—" if the user has no expenses.
    """
    month_start = date.today().replace(day=1).isoformat()

    conn = get_db()
    try:
        totals = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count "
            "FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        month = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total "
            "FROM expenses WHERE user_id = ? AND date >= ?",
            (user_id, month_start),
        ).fetchone()
        top = conn.execute(
            "SELECT category, SUM(amount) AS total FROM expenses "
            "WHERE user_id = ? GROUP BY category "
            "ORDER BY total DESC, category ASC LIMIT 1",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()

    return {
        "total_spent": float(totals["total"]),
        "month_spent": float(month["total"]),
        "transaction_count": totals["count"],
        "top_category": top["category"] if top else "—",
    }
