"""Seed a single dummy Indian user into the Spendly database."""
import os
import random
import sys
from datetime import datetime

from werkzeug.security import generate_password_hash

# Make the project's database package importable.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database.db import get_db  # noqa: E402


# Realistic Indian first names drawn from different regions/communities.
FIRST_NAMES = [
    # North
    "Rahul", "Priya", "Amit", "Neha", "Vikram", "Anjali", "Rohit", "Pooja",
    "Sandeep", "Kavita", "Arjun", "Sneha",
    # South
    "Arun", "Deepa", "Karthik", "Lakshmi", "Ramesh", "Divya", "Suresh", "Anitha",
    "Vijay", "Meenakshi",
    # East
    "Suman", "Pallavi", "Ravi", "Srabanti", "Biswajit", "Ananya",
    # West
    "Harsh", "Nisha", "Kunal", "Riya", "Aditya", "Tanvi",
    # Central / misc
    "Manish", "Shalini", "Gaurav", "Aishwarya", "Siddharth", "Megha",
]

# Common Indian last names spanning regions and communities.
LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Gupta", "Iyer", "Reddy", "Nair", "Khan",
    "Singh", "Kumar", "Das", "Mukherjee", "Banerjee", "Chatterjee", "Joshi",
    "Mehta", "Shah", "Kapoor", "Bhat", "Menon", "Pillai", "Rao", "Saxena",
    "Agarwal", "Tiwari", "Mishra", "Pandey", "Chauhan", "Yadav", "Bose",
    "Roy", "Sengupta", "Desai", "Kulkarni", "Bajaj", "Jain", "Srinivasan",
]

# Common personal email providers in India.
EMAIL_DOMAINS = [
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "rediffmail.com",
]


def generate_user():
    """Generate a random Indian user as a dict."""
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    suffix = random.randint(10, 999)  # 2–3 digit number
    domain = random.choice(EMAIL_DOMAINS)
    # email handle uses lowercase first.last
    handle = f"{first.lower()}.{last.lower()}{suffix}"
    email = f"{handle}@{domain}"
    name = f"{first} {last}"
    return {
        "name": name,
        "email": email,
        "password_hash": generate_password_hash("password123"),
        "created_at": datetime.now().isoformat(sep=" ", timespec="seconds"),
    }


def main():
    conn = get_db()
    try:
        # Keep regenerating until we land on a unique email.
        while True:
            user = generate_user()
            existing = conn.execute(
                "SELECT id FROM users WHERE email = ?", (user["email"],)
            ).fetchone()
            if existing is None:
                break

        # Insert the user using the same parameterized pattern as db.py.
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash, created_at) "
            "VALUES (?, ?, ?, ?)",
            (
                user["name"],
                user["email"],
                user["password_hash"],
                user["created_at"],
            ),
        )
        conn.commit()
        new_id = cur.lastrowid

        print("Dummy user created successfully.")
        print(f"  id:    {new_id}")
        print(f"  name:  {user['name']}")
        print(f"  email: {user['email']}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
