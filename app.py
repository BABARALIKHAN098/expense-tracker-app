import os
import sqlite3

from flask import Flask, render_template, request, redirect, url_for, session

from database.db import (
    get_db,
    init_db,
    seed_db,
    find_user_by_email,
    create_user,
    get_user_by_id,
    count_expenses_for_user,
    get_total_spent_for_user,
    get_top_category_for_user,
    get_recent_expenses_for_user,
    get_category_breakdown_for_user,
)
from database.auth import hash_password, verify_password

app = Flask(__name__)
# Override the SECRET_KEY env var in production. The dev fallback is intentionally
# obvious so it never silently leaks into a deployed environment.
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")


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


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip()
    password = request.form.get("password") or ""

    error = None
    if not name:
        error = "Please enter your name."
    elif not email:
        error = "Please enter your email address."
    elif not password:
        error = "Please choose a password."
    elif "@" not in email or "." not in email:
        error = "Please enter a valid email address."
    elif len(password) < 8:
        error = "Password must be at least 8 characters."
    elif find_user_by_email(email) is not None:
        error = "An account with that email already exists."
    else:
        try:
            new_id = create_user(name, email, hash_password(password))
        except sqlite3.IntegrityError:
            # Backstop for the race where two requests with the same email both
            # pass the find_user_by_email check before either insert commits.
            error = "An account with that email already exists."
        else:
            session["user_id"] = new_id
            session["user_name"] = name
            return redirect(url_for("profile"))

    return render_template("register.html", name=name, email=email, error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = (request.form.get("email") or "").strip()
    password = request.form.get("password") or ""

    error = None
    if not email:
        error = "Please enter your email address."
    elif not password:
        error = "Please enter your password."
    else:
        row = find_user_by_email(email)
        if row is None or not verify_password(password, row["password_hash"]):
            # Generic error — do not leak which field failed.
            error = "Invalid email or password."
        else:
            session["user_id"] = row["id"]
            session["user_name"] = row["name"]
            return redirect(url_for("profile"))

    return render_template("login.html", email=email, error=error)


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    return "Logout — coming in Step 3"


@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if user_id is None:
        return redirect(url_for("login"))

    user = get_user_by_id(user_id)
    if user is None:
        # Session points at a deleted user — clear and bounce to login.
        session.clear()
        return redirect(url_for("login"))

    # Format member-since as "Joined <Month> <Year>" without importing
    # datetime into the template. SQLite default is "YYYY-MM-DD HH:MM:SS".
    month_names = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]
    date_part = (user["created_at"] or "").split(" ")[0]
    year, month, _ = date_part.split("-")
    member_since = f"Joined {month_names[int(month) - 1]} {year}"

    expense_count = count_expenses_for_user(user_id)
    total_spent = get_total_spent_for_user(user_id)
    top_category = get_top_category_for_user(user_id)
    recent_expenses = get_recent_expenses_for_user(user_id, limit=10)
    category_breakdown = get_category_breakdown_for_user(user_id)

    # Format each row's date as "12 Apr 2025" and amount as ₹1,234.56.
    display_rows = []
    for row in recent_expenses:
        iso_date = row["date"] or ""
        try:
            y, m, d = iso_date.split("-")
            short_date = f"{int(d)} {month_names[int(m) - 1][:3]} {y}"
        except (ValueError, IndexError):
            short_date = iso_date
        display_rows.append({
            "id": row["id"],
            "date": short_date,
            "description": row["description"] or "—",
            "category": row["category"],
            "amount": f"₹{row['amount']:,.2f}",
        })

    breakdown_max = max((b["total"] for b in category_breakdown), default=0) or 1
    display_breakdown = [
        {
            "category": b["category"],
            "total": f"₹{b['total']:,.2f}",
            "percent": round((b["total"] / breakdown_max) * 100),
        }
        for b in category_breakdown
    ]

    return render_template(
        "profile.html",
        user=user,
        member_since=member_since,
        expense_count=expense_count,
        total_spent=f"₹{total_spent:,.2f}",
        top_category=top_category or "—",
        recent_expenses=display_rows,
        category_breakdown=display_breakdown,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
