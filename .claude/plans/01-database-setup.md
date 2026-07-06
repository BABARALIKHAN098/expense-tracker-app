# Step 1 — Database Setup: Implementation Plan

## Context

Spendly is a Flask + SQLite personal expense tracker. Step 1 establishes the data layer foundation: a `database/db.py` module exposing `get_db()`, `init_db()`, and `seed_db()`, plus a one-line DB bootstrap inside `app.py` at module load.

The spec (`.claude/specs/01-database-setup.md`) mandates:

- A SQLite database file (`spendly.db`) in the project root
- Two tables — `users` and `expenses` — with the exact schema listed in the spec
- Foreign-key enforcement enabled on every connection
- An idempotent seed: one demo user (`demo@spendly.com` / `demo123`, hashed via `werkzeug.security`) and 8 sample expenses covering all 7 fixed categories
- No new pip packages, no new files, no new routes

Every later step (auth, profile, expense CRUD) depends on this foundation being correct.

---

## Files to modify

| File | Change |
|---|---|
| `database/db.py` | Replace the stub comment with the full implementation of `get_db()`, `init_db()`, `seed_db()`, plus two schema constants. |
| `app.py` | Add an import of the three helpers and a small `with app.app_context():` block that calls `init_db()` then `seed_db()` before any route runs. |
| `.gitignore` | Append `spendly.db` and `spendly.db-journal` so the DB file is not committed. |

No other files change. No new files are created.

---

## `database/db.py` — full design

### Imports

```python
import os
import sqlite3
from datetime import date, timedelta

from werkzeug.security import generate_password_hash
```

### Module-level constants

```python
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
```

### Functions

```python
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
                (user_id, amount, category,
                 first_of_month.replace(day=day).isoformat(),
                 description),
            )

        conn.commit()
    finally:
        conn.close()
```

### Seed coverage matrix

| # | amount  | category       | day | description        |
|---|---------|----------------|-----|--------------------|
| 1 | 12.50   | Food           | 1   | Lunch at cafe      |
| 2 | 45.00   | Transport      | 3   | Weekly bus pass    |
| 3 | 89.99   | Bills          | 5   | Internet bill      |
| 4 | 32.40   | Health         | 7   | Pharmacy           |
| 5 | 15.00   | Entertainment  | 8   | Movie ticket       |
| 6 | 60.00   | Shopping       | 10  | New shoes          |
| 7 | 22.75   | Other          | 12  | Misc household     |
| 8 |  8.20   | Food           | 14  | Morning coffee     |

All 7 fixed categories appear (Food twice to reach the 8-row count). Dates use `YYYY-MM-DD` from `date.isoformat()`. Dates are clamped to the current month via `first_of_month.replace(day=day)`, which is safe through day 28 in every month.

---

## `app.py` — full design

Add the import at the top, then a tiny bootstrap block right after `app = Flask(__name__)` and before any route.

```python
from flask import Flask, render_template

from database.db import get_db, init_db, seed_db

app = Flask(__name__)


# ------------------------------------------------------------------ #
# Database bootstrap                                                  #
# ------------------------------------------------------------------ #
with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #
@app.route("/")
def landing():
    return render_template("landing.html")

# ... existing routes unchanged ...
```

No other lines in `app.py` change. The `if __name__ == "__main__":` block keeps `app.run(debug=True, port=5001)`.

---

## `.gitignore` — full change

Append these two lines to the existing Django/Flask block (around line 60, next to `db.sqlite3`):

```
spendly.db
spendly.db-journal
```

---

## Design decisions

- **DB file name: `spendly.db`.** Matches the project name. Added to `.gitignore` (the existing `db.sqlite3` and `instance/` entries don't cover it).
- **Absolute DB path via `os.path.abspath(__file__)`.** Lets the dev server be started from any directory; the DB always lands in the project root.
- **Schema as two module-level constants joined by `executescript`.** DDL stays visible at the top of the file; `CREATE TABLE IF NOT EXISTS` makes `init_db()` safe to call repeatedly.
- **`FOREIGN KEY` declared inline in the `expenses` `CREATE TABLE`.** Standard SQLite pattern; `PRAGMA foreign_keys = ON` on every connection enforces it.
- **Idempotency: `SELECT COUNT(*) FROM users` early-return.** Simple and correct; also handles Flask's debug-mode auto-reloader (the module runs twice in quick succession on a debug restart, but only the first run actually inserts).
- **No Flask `g` object.** Spec doesn't require request-scoped connections, and the existing `app.py` doesn't use `g`. Each helper opens and closes its own connection explicitly.
- **No new pip packages.** `sqlite3`, `datetime` are stdlib; `werkzeug.security` is already installed.
- **Password hashing uses `werkzeug.security.generate_password_hash("demo123")` with default algorithm.** Modern werkzeug uses scrypt by default; either scrypt or pbkdf2 is acceptable for a demo seed.
- **Dates derived at runtime from `date.today()`.** Keeps the seed feeling "fresh" each month and guarantees `YYYY-MM-DD`.

---

## Verification

Run these in order from the project root `C:\Users\babar\OneDrive\Desktop\expense-tracker\expense-tracker`:

1. **Clean slate:**
   ```bash
   rm -f spendly.db spendly.db-journal
   ```

2. **Boot the dev server cleanly:**
   ```bash
   python app.py
   ```
   Expect no traceback. Cancel with `Ctrl-C` after the first log line.

3. **Confirm the DB file was created:**
   ```bash
   ls -la spendly.db
   ```

4. **Inspect schema:**
   ```bash
   sqlite3 spendly.db ".schema"
   ```
   Expect both `CREATE TABLE users` and `CREATE TABLE expenses` with the spec'd columns and constraints.

5. **Inspect the seeded user:**
   ```bash
   sqlite3 spendly.db "SELECT id, name, email, substr(password_hash, 1, 20) || '...' FROM users;"
   ```
   Expect one row: `Demo User` / `demo@spendly.com` / a hashed prefix (NOT the literal `demo123`).

6. **Confirm all 7 categories are represented:**
   ```bash
   sqlite3 spendly.db "SELECT category, COUNT(*) FROM expenses GROUP BY category ORDER BY category;"
   ```
   Expect 7 rows totalling 8: `Bills=1, Entertainment=1, Food=2, Health=1, Other=1, Shopping=1, Transport=1`.

7. **Confirm idempotency — restart and re-count:**
   ```bash
   python app.py   # second run
   sqlite3 spendly.db "SELECT COUNT(*) FROM users; SELECT COUNT(*) FROM expenses;"
   ```
   Expect `1` and `8` (unchanged).

8. **FK enforcement — invalid `user_id` should fail:**
   ```bash
   sqlite3 spendly.db "INSERT INTO expenses (user_id, amount, category, date) VALUES (999, 10, 'Food', '2026-07-01');"
   ```
   Expect `Runtime error: FOREIGN KEY constraint failed`.

9. **UNIQUE constraint — duplicate email should fail:**
   ```bash
   sqlite3 spendly.db "INSERT INTO users (name, email, password_hash) VALUES ('x', 'demo@spendly.com', 'x');"
   ```
   Expect `Runtime error: UNIQUE constraint failed: users.email`.

10. **Confirm `.gitignore` covers the DB file:**
    ```bash
    git check-ignore -v spendly.db
    ```
    Expect output naming `.gitignore` as the matching rule.

---

## Risks / open questions

- **Short-month edge case:** seed dates go up to day 14, which is safe in every month (February has 28). The `first_of_month.replace(day=day)` call would raise `ValueError` for `day > days_in_month`, but with `day=14` this never triggers.
- **Hash algorithm drift:** modern werkzeug (3.1.x) defaults to scrypt. If a future step needs to *verify* this password, it will Just Work via `check_password_hash`. No action needed now.
- **Flask debug auto-reloader:** the `COUNT(*)` guard handles the double-execution correctly.
- **No tests/ directory is created.** The spec says "No new files" in section 8. Manual verification with the `sqlite3` CLI is sufficient for Step 1; a tests/ directory can be introduced in a later step that has explicit testing requirements.
