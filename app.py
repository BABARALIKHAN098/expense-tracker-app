import os
import sqlite3

from flask import Flask, render_template, request, redirect, url_for, session

from database.db import get_db, init_db, seed_db, find_user_by_email, create_user
from database.auth import hash_password

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


@app.route("/login")
def login():
    return render_template("login.html")


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
    return "Profile page — coming in Step 4"


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
