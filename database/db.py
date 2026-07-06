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
