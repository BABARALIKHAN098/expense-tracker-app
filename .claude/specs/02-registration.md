# Spec: Registration

## Overview
Turn the existing `/register` GET-only route into a working account-creation flow. A new visitor submits their name, email, and password; the app validates the input, hashes the password with werkzeug, inserts a new row into the `users` table, and logs them in by storing their `user_id` in the Flask session before redirecting to `/profile`. This is the first step that mutates the database from a request, so it establishes the patterns — parameterized writes, hashed passwords, server-side validation, flash-style error rendering — that every subsequent auth flow will reuse.

## Depends on
- Step 1 (Database setup) — the `users` table with `id`, `name`, `email`, `password_hash`, and `created_at` columns must already exist, and `get_db()` must enforce `PRAGMA foreign_keys = ON`.

## Routes
- `GET  /register` — render the registration form (existing route) — public
- `POST /register` — validate input, create the user, log them in, redirect to `/profile` — public

## Database changes
No database changes. The `users` table created in Step 1 already has the required columns and constraints. Registration only inserts rows — no schema migrations.

## Templates
- **Create:** none
- **Modify:**
  - `templates/register.html` — the form already posts to `/register`, so no structural change is required. Implementation will:
    - Re-render the same template (not redirect) on validation failure, passing back the submitted `name` and `email` so the user does not have to retype them, and a human-readable `error` message.
    - On success, redirect to `/profile` (the existing stub) and let the welcome live there for now.

## Files to change
- `app.py` — change the `register` view to accept both GET and POST, add session handling, and add a small auth helper module import.
- `database/db.py` — add two helpers: `create_user(name, email, password)` (inserts a hashed user, returns the new `id`) and `find_user_by_email(email)` (returns the row or `None`). Keep `get_db`, `init_db`, `seed_db` untouched.
- `templates/register.html` — repopulate `name` and `email` fields from the form on validation error; keep the `error` banner that already exists.

## Files to create
- `database/auth.py` — small module with one helper, `hash_password(plain)` wrapping `werkzeug.security.generate_password_hash`, so the hashing call is not duplicated between `database/db.py` and future auth steps (login, password reset, etc.).

## New dependencies
No new dependencies. `werkzeug` and `flask` are already in `requirements.txt`.

## Rules for implementation
- No SQLAlchemy or any ORM — raw `sqlite3` only, with `?` placeholders for every write.
- Hash every password with `werkzeug.security.generate_password_hash` (default scrypt) before it is written to disk; never store plain text.
- Use the application `SECRET_KEY` (set at module level in `app.py` from env, with a documented dev fallback) so Flask's `session` cookie is signed.
- Reject empty fields, an email that does not contain `@` and a `.`, and a password shorter than 8 characters — return the form with a specific error message for each, do not redirect.
- On duplicate email, return the form with `"An account with that email already exists."` — do not leak which field collided beyond that phrasing.
- On success, write `session["user_id"] = new_id` and `session["user_name"] = new_name` and `return redirect(url_for("profile"))`.
- Routes must call helpers in `database/db.py`, never run SQL inline.
- Use `url_for("register")`, `url_for("login")`, `url_for("profile")` in the template — no hardcoded URLs.
- All templates extend `base.html`; do not add inline `<style>` blocks; the existing auth classes (`.auth-section`, `.auth-card`, `.form-input`, `.btn-submit`, `.auth-error`) already live in `static/css/style.css` and use CSS variables — do not introduce new hex values.
- Vanilla JS only, no new scripts required for this step.

## Definition of done
- [ ] `GET /register` still renders the existing form.
- [ ] Submitting the form with all three fields filled in creates a new row in the `users` table whose `password_hash` starts with `scrypt:` (or the current werkzeug default prefix).
- [ ] Submitting with an empty name, empty email, empty password, malformed email, or password shorter than 8 characters re-renders the form with a visible `auth-error` message and the `name`/`email` values preserved.
- [ ] Submitting an email that already exists in the database re-renders the form with `"An account with that email already exists."` and does **not** create a second row.
- [ ] After a successful submit, the response is a 302 redirect to `/profile`, and the user's browser now sends a `session` cookie signed by the app's `SECRET_KEY`.
- [ ] After registration, visiting `/register` again still works (does not crash if the user is already logged in — that nuance is fine to defer to Step 3).
- [ ] No SQL string interpolation anywhere in `app.py` or `database/db.py` — every write uses `?` placeholders.
- [ ] `app.py` runs without errors on `python app.py` against a fresh `spendly.db`, and `pytest` still passes (the existing test suite must remain green; new tests for registration helpers live in `tests/test_registration.py`).
