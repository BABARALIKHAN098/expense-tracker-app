import os
import sqlite3
from datetime import date

from werkzeug.security import generate_password_hash


# Absolute path to spendly.db in the project root, regardless of CWD.
DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "spendly.db",
)

SCHEMA_USERS = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

SCHEMA_EXPENSES = """
CREATE TABLE IF NOT EXISTS expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    amount      REAL    NOT NULL,
    category    TEXT    NOT NULL,
    date        TEXT    NOT NULL,
    description TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""


def get_db():
    """Return a SQLite connection with row_factory and FK enforcement on."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create the users and expenses tables (idempotent)."""
    conn = get_db()
    try:
        conn.executescript(SCHEMA_USERS + SCHEMA_EXPENSES)
        conn.commit()
    finally:
        conn.close()


def seed_db():
    """Insert one demo user and 8 sample expenses (idempotent)."""
    conn = get_db()
    try:
        # Idempotency: bail out if users table already has any rows.
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count > 0:
            return

        # One demo user.
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
        )

        # Look up the new user's id.
        user_id = conn.execute(
            "SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)
        ).fetchone()["id"]

        # 8 sample expenses, spread across the current month, all 7 categories.
        first_of_month = date.today().replace(day=1)

        # (amount, category, day_of_month, description)
        sample_expenses = [
            (12.50, "Food",           1,  "Lunch at cafe"),
            (45.00, "Transport",      3,  "Weekly bus pass"),
            (89.99, "Bills",          5,  "Internet bill"),
            (32.40, "Health",         7,  "Pharmacy"),
            (15.00, "Entertainment",  8,  "Movie ticket"),
            (60.00, "Shopping",      10,  "New shoes"),
            (22.75, "Other",         12,  "Misc household"),
            ( 8.20, "Food",          14,  "Morning coffee"),
        ]

        for amount, category, day, description in sample_expenses:
            conn.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    user_id,
                    amount,
                    category,
                    first_of_month.replace(day=day).isoformat(),
                    description,
                ),
            )

        conn.commit()
    finally:
        conn.close()


def find_user_by_email(email: str):
    """Return the users row matching `email` (case-insensitive), or None."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE LOWER(email) = LOWER(?)",
            (email,),
        ).fetchone()
    finally:
        conn.close()


def get_user_by_id(user_id: int):
    """Return the users row matching `user_id`, or None."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()


# The seven categories a user can pick from in the /profile filter.
# Kept here (not in app.py) so the DB layer and the route layer agree on
# what counts as a valid category.
ALLOWED_CATEGORIES = (
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
)


def _apply_expense_filters(start_date=None, end_date=None, category=None):
    """Build a (extra_clauses, params) pair for the five expense query helpers.

    Returns JUST the extra AND-clauses (without the WHERE keyword) and the
    params to bind to them. Callers are expected to write:

        WHERE user_id = ? <extra_clauses>

    so we never get duplicate WHERE keywords when filters are absent or
    present.

    Any filter that is None or otherwise invalid is simply skipped, so
    callers can pass the raw values straight from request.args and trust
    the helper to ignore the bad ones.
    """
    clauses = []
    params = []

    if start_date:
        clauses.append("date >= ?")
        params.append(start_date)
    if end_date:
        clauses.append("date <= ?")
        params.append(end_date)
    if category:
        clauses.append("category = ?")
        params.append(category)

    extra = (" AND " + " AND ".join(clauses)) if clauses else ""
    return extra, params


def count_expenses_for_user(
    user_id: int,
    start_date=None,
    end_date=None,
    category=None,
) -> int:
    """Return the number of expenses owned by `user_id`, optionally filtered."""
    extra, params = _apply_expense_filters(start_date, end_date, category)
    conn = get_db()
    try:
        return conn.execute(
            f"SELECT COUNT(*) FROM expenses WHERE user_id = ?{extra}",
            (user_id, *params),
        ).fetchone()[0]
    finally:
        conn.close()


def get_total_spent_for_user(
    user_id: int,
    start_date=None,
    end_date=None,
    category=None,
) -> float:
    """Return the sum of all expense amounts for `user_id` (0.0 if none), optionally filtered."""
    extra, params = _apply_expense_filters(start_date, end_date, category)
    conn = get_db()
    try:
        row = conn.execute(
            f"SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE user_id = ?{extra}",
            (user_id, *params),
        ).fetchone()
        return float(row[0])
    finally:
        conn.close()


def get_top_category_for_user(
    user_id: int,
    start_date=None,
    end_date=None,
    category=None,
):
    """Return the category name with the highest total spend, or None if no expenses.

    Tie-breaking is alphabetical so the result is deterministic.

    The `category` filter is intentionally ignored for this helper — asking
    "what's my top category within a single category?" is meaningless, so
    we report the top category from the broader date-windowed set instead.
    """
    # Drop the category filter; keep the date range.
    extra, params = _apply_expense_filters(start_date=start_date, end_date=end_date)
    conn = get_db()
    try:
        row = conn.execute(
            f"""
            SELECT category, SUM(amount) AS total
            FROM expenses
            WHERE user_id = ?{extra}
            GROUP BY category
            ORDER BY total DESC, category ASC
            LIMIT 1
            """,
            (user_id, *params),
        ).fetchone()
        return row["category"] if row is not None else None
    finally:
        conn.close()


def get_recent_expenses_for_user(
    user_id: int,
    limit: int = 10,
    start_date=None,
    end_date=None,
    category=None,
):
    """Return up to `limit` expenses for `user_id`, newest first, optionally filtered.

    Each row is a sqlite3.Row with id, amount, category, date, description.
    """
    extra, params = _apply_expense_filters(start_date, end_date, category)
    conn = get_db()
    try:
        return conn.execute(
            f"""
            SELECT id, amount, category, date, description
            FROM expenses
            WHERE user_id = ?{extra}
            ORDER BY date DESC, id DESC
            LIMIT ?
            """,
            (user_id, *params, limit),
        ).fetchall()
    finally:
        conn.close()


def get_category_breakdown_for_user(
    user_id: int,
    start_date=None,
    end_date=None,
    category=None,
):
    """Return a list of (category, total) rows for `user_id`, biggest first, optionally filtered.

    The `category` filter is dropped here for the same reason as
    `get_top_category_for_user` — filtering to one category would leave
    at most one row, defeating the breakdown's purpose.

    Each entry is a sqlite3.Row with 'category' and 'total' (REAL).
    """
    extra, params = _apply_expense_filters(start_date=start_date, end_date=end_date)
    conn = get_db()
    try:
        return conn.execute(
            f"""
            SELECT category, SUM(amount) AS total
            FROM expenses
            WHERE user_id = ?{extra}
            GROUP BY category
            ORDER BY total DESC, category ASC
            """,
            (user_id, *params),
        ).fetchall()
    finally:
        conn.close()


def create_user(name: str, email: str, password_hash: str) -> int:
    """Insert a new user and return the new row's id. Caller passes an already-hashed password.

    Raises sqlite3.IntegrityError on UNIQUE constraint violations (duplicate email);
    the route catches that and maps it to a user-facing error.
    """
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()
