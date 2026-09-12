"""Category-breakdown query helper for the profile page.

Pure data-access module: raw sqlite3 via ``get_db()``, no Flask imports,
no ORM. Every query is scoped to a single user with a parameterised
``WHERE user_id = ?`` clause.
"""

from database.db import get_db


def get_category_breakdown(user_id):
    """Return this user's spend grouped by category, largest first.

    Each item is a plain dict: ``{"name": str, "amount": float, "pct": int}``.
    ``pct` is the integer percentage of the user's total spend that the
    category accounts for. Only categories the user has actually spent
    money in are included (never padded out to the full category list).
    Returns ``[]`` for a user with no expenses, and never raises for a
    missing/unknown user.
    """
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT category, SUM(amount) AS total FROM expenses "
            "WHERE user_id = ? "
            "GROUP BY category "
            "ORDER BY total DESC, category ASC",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return []

    amounts = [float(row["total"]) for row in rows]
    grand_total = sum(amounts)
    if grand_total <= 0:
        return []

    # Integer-round each category's share of the total. Rounding every
    # percentage independently almost never sums to exactly 100 (it can
    # land on 99 or 101 depending on the fractional remainders), so after
    # computing the naive rounded values we work out the leftover
    # difference and add it to the LARGEST category. That category has
    # the biggest absolute amount, so a +-1 nudge there is the least
    # noticeable and keeps the displayed percentages summing to 100.
    raw_pcts = [amount / grand_total * 100 for amount in amounts]
    pcts = [round(p) for p in raw_pcts]
    remainder = 100 - sum(pcts)
    if remainder != 0:
        largest_index = amounts.index(max(amounts))
        pcts[largest_index] += remainder

    return [
        {"name": row["category"], "amount": amounts[i], "pct": pcts[i]}
        for i, row in enumerate(rows)
    ]
