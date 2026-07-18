"""Tests for the /login endpoint and the /profile view."""

from database.db import get_user_by_id


# Seeded by database.db.seed_db: demo@spendly.com / demo123
DEMO_EMAIL = "demo@spendly.com"
DEMO_PASSWORD = "demo123"

# Custom user we create for login tests so the seeded demo user stays put.
TEST_EMAIL = "logintester@example.com"
TEST_PASSWORD = "loginpass123"
TEST_NAME = "Login Tester"


def _create_test_user(client):
    """Helper: create a user via the public /register endpoint."""
    client.post(
        "/register",
        data={"name": TEST_NAME, "email": TEST_EMAIL, "password": TEST_PASSWORD},
    )


# ------------------------------------------------------------------ #
# /login GET                                                          #
# ------------------------------------------------------------------ #

def test_get_login_renders_form(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Welcome back" in response.data


# ------------------------------------------------------------------ #
# /login POST — happy path                                            #
# ------------------------------------------------------------------ #

def test_valid_login_redirects_to_profile_and_sets_session(client):
    _create_test_user(client)
    response = client.post(
        "/login",
        data={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")
    assert "session=" in response.headers.get("Set-Cookie", "")


# ------------------------------------------------------------------ #
# /login POST — failures (no leak between unknown user / wrong pw)    #
# ------------------------------------------------------------------ #

def test_unknown_email_returns_generic_error(client):
    response = client.post(
        "/login",
        data={"email": "ghost@example.com", "password": "whatever1"},
    )
    assert response.status_code == 200
    assert b"Invalid email or password." in response.data
    # The submitted email is preserved so the user can fix it.
    assert b"ghost@example.com" in response.data


def test_wrong_password_returns_same_generic_error(client):
    _create_test_user(client)
    response = client.post(
        "/login",
        data={"email": TEST_EMAIL, "password": "wrongpass1"},
    )
    assert response.status_code == 200
    assert b"Invalid email or password." in response.data
    # Form must NOT distinguish "no such user" from "wrong password".
    assert b"not found" not in response.data.lower()
    assert b"incorrect password" not in response.data.lower()
    assert b"no such user" not in response.data.lower()


# ------------------------------------------------------------------ #
# /login POST — validation                                            #
# ------------------------------------------------------------------ #

def test_empty_email_re_renders(client):
    response = client.post("/login", data={"email": "", "password": "x"})
    assert response.status_code == 200
    assert b"Please enter your email address." in response.data


def test_empty_password_re_renders(client):
    response = client.post("/login", data={"email": "a@b.com", "password": ""})
    assert response.status_code == 200
    assert b"Please enter your password." in response.data


# ------------------------------------------------------------------ #
# /profile — auth guard                                               #
# ------------------------------------------------------------------ #

def test_profile_anonymous_redirects_to_login(client):
    response = client.get("/profile", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_profile_logged_in_shows_user_data(client):
    _create_test_user(client)
    # Explicitly log in (registration already set the session on the same
    # client, but be explicit so the test stays self-contained).
    client.post(
        "/login",
        data={"email": TEST_EMAIL, "password": TEST_PASSWORD},
    )
    response = client.get("/profile")
    assert response.status_code == 200
    assert TEST_NAME.encode() in response.data
    assert TEST_EMAIL.encode() in response.data
    # The member-since line shows "Joined <Month> <Year>".
    assert b"Joined " in response.data
    # TEST_EMAIL has 0 expenses → zero stats, empty panels.
    assert b"Recent Transactions" in response.data
    assert b"By Category" in response.data
    assert b"Top category" in response.data
    # 0 expenses → "₹0.00" total.
    assert b"\xe2\x82\xb90.00" in response.data


def test_profile_logged_in_counts_own_expenses(client):
    # Use the seeded demo user, who has 8 expenses.
    client.post(
        "/login",
        data={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )
    response = client.get("/profile")
    assert response.status_code == 200
    assert b"Demo User" in response.data
    # 8 transactions in the stat tile.
    assert b">8<" in response.data
    # Total spent: 12.50 + 45 + 89.99 + 32.40 + 15 + 60 + 22.75 + 8.20 = 285.84
    assert b"285.84" in response.data
    # Top category is the single highest: Bills at 89.99.
    assert b"Bills" in response.data
    # At least one category row in the breakdown.
    assert b"profile-bar" in response.data
    # Table is rendered with header cells.
    assert b"Recent Transactions" in response.data
    assert b"<th>Date</th>" in response.data
    assert b"<th>Description</th>" in response.data
    assert b"<th>Category</th>" in response.data
    assert b"<th" in response.data and b"Amount</th>" in response.data


def test_profile_table_renders_eight_rows_for_demo_user(client):
    client.post(
        "/login",
        data={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )
    response = client.get("/profile")
    # 8 seeded expenses → 8 <tr> rows in the table body (one extra in thead).
    body = response.data.split(b"<tbody>")[1].split(b"</tbody>")[0]
    assert body.count(b"<tr>") == 8


def test_profile_breakdown_has_seven_categories_for_demo_user(client):
    client.post(
        "/login",
        data={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )
    response = client.get("/profile")
    # The seed data covers all 7 categories.
    for cat in (b"Food", b"Transport", b"Bills", b"Health",
                b"Entertainment", b"Shopping", b"Other"):
        assert cat in response.data


def test_profile_session_for_deleted_user_clears_and_redirects(client):
    # Manually plant a session whose user_id no longer exists, then GET /profile.
    with client.session_transaction() as sess:
        sess["user_id"] = 99999
        sess["user_name"] = "Ghost"

    response = client.get("/profile", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


# ------------------------------------------------------------------ #
# Navbar flips on session                                             #
# ------------------------------------------------------------------ #

def test_navbar_shows_signin_when_anonymous(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Sign in" in response.data
    assert b"Sign out" not in response.data


def test_navbar_shows_username_when_logged_in(client):
    _create_test_user(client)
    response = client.get("/")
    assert response.status_code == 200
    assert TEST_NAME.encode() in response.data
    assert b"Sign out" in response.data
    # When logged in, the "Get started" CTA must NOT appear.
    assert b"Get started" not in response.data
