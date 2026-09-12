"""Single import surface for the profile page's read queries.

The implementations live in one module per data concern so each can be
read and tested on its own:
    queries_summary      - get_user_by_id, get_summary_stats
    queries_transactions - get_recent_transactions
    queries_categories   - get_category_breakdown

Views should import from here rather than reaching into the individual
modules, so the split stays an implementation detail.
"""

from database.queries_categories import get_category_breakdown
from database.queries_summary import get_summary_stats, get_user_by_id
from database.queries_transactions import get_recent_transactions

__all__ = [
    "get_category_breakdown",
    "get_recent_transactions",
    "get_summary_stats",
    "get_user_by_id",
]
