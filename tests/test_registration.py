"""Tests for the /register endpoint and its supporting helpers."""

from database.auth import hash_password
from database.db import find_user_by_email


# All "happy path" inputs use these — adjust if you change the validation rules.
VALID_NAME = "New User"
VALID_EMAIL = "newuser@example.com"
VALID_PASSWORD = "password123"


# ------------------------------------------------------------------ #
# GET                                                                #
# ------------------------------------------------------------------ #

def test_get_register_renders_form(client):
    response = client.get("/register")
    assert response.status_code == 200
    assert b"Create your account" in response.data


# ------------------------------------------------------------------ #
# POST — happy path                                                  #
# ------------------------------------------------------------------ #

def test_valid_post_creates_user_and_redirects(client):
    response = client.post(
        "/register",
        data={"name": VALID_NAME, "email": VALID_EMAIL, "password": VALID_PASSWORD},
        follow_redirects=False,
    )

    # Redirect to /profile (the existing stub).
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")

    # The row exists with a hashed password — never the plain text.
    row = find_user_by_email(VALID_EMAIL)
    assert row is not None
    assert row["name"] == VALID_NAME
    assert row["password_hash"] != VALID_PASSWORD
    assert row["password_hash"].startswith("scrypt:")


def test_session_cookie_set_on_success(client):
    response = client.post(
        "/register",
        data={"name": VALID_NAME, "email": VALID_EMAIL, "password": VALID_PASSWORD},
    )
    # Flask's secure session cookie is named "session".
    set_cookie = response.headers.get("Set-Cookie", "")
    assert "session=" in set_cookie


# ------------------------------------------------------------------ #
# POST — validation failures                                         #
# ------------------------------------------------------------------ #

def test_empty_name_re_renders_with_error(client):
    response = client.post(
        "/register",
        data={"name": "", "email": VALID_EMAIL, "password": VALID_PASSWORD},
    )
    assert response.status_code == 200
    assert b"Please enter your name." in response.data
    # Name is empty so the input value should also be empty.
    assert b'value=""' in response.data
    # Email was valid and should be preserved.
    assert VALID_EMAIL.encode() in response.data


def test_empty_email_re_renders_with_error(client):
    response = client.post(
        "/register",
        data={"name": VALID_NAME, "email": "", "password": VALID_PASSWORD},
    )
    assert response.status_code == 200
    assert b"Please enter your email address." in response.data
    # Name should be preserved.
    assert VALID_NAME.encode() in response.data


def test_malformed_email_re_renders_with_error(client):
    response = client.post(
        "/register",
        data={"name": VALID_NAME, "email": "notanemail", "password": VALID_PASSWORD},
    )
    assert response.status_code == 200
    assert b"Please enter a valid email address." in response.data
    # The bad email is preserved so the user can fix it.
    assert b"notanemail" in response.data


def test_short_password_re_renders_with_error(client):
    response = client.post(
        "/register",
        data={"name": VALID_NAME, "email": VALID_EMAIL, "password": "abc"},
    )
    assert response.status_code == 200
    assert b"Password must be at least 8 characters." in response.data


# ------------------------------------------------------------------ #
# POST — duplicate email                                             #
# ------------------------------------------------------------------ #

def test_duplicate_email_returns_specific_error(client):
    payload = {"name": VALID_NAME, "email": VALID_EMAIL, "password": VALID_PASSWORD}

    first = client.post("/register", data=payload)
    assert first.status_code == 302  # first registration succeeds

    second = client.post("/register", data=payload)
    assert second.status_code == 200
    assert b"An account with that email already exists." in second.data

    # The DB must still have exactly one row for this email.
    from database.db import get_db
    conn = get_db()
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM users WHERE email = ?", (VALID_EMAIL,)
        ).fetchone()[0]
    finally:
        conn.close()
    assert count == 1


# ------------------------------------------------------------------ #
# Helper sanity check                                                #
# ------------------------------------------------------------------ #

def test_hash_password_is_not_plaintext():
    h = hash_password("password123")
    assert h != "password123"
    assert h.startswith("scrypt:")
