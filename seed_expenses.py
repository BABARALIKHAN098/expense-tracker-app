"""Seed realistic dummy expenses for a single user.

Usage:
    python seed_expenses.py <user_id> <count> <months>
"""
import random
import sys
from datetime import date, timedelta

from database.db import get_db


# Realistic Indian-context descriptions per category, with (min, max) amount in INR.
CATEGORIES = {
    "Food": (
        50, 800,
        [
            "Chai and samosa",
            "Lunch at Saravana Bhavan",
            "Biryani from Paradise",
            "Dosa at Indian Coffee House",
            "Pav bhaji at street stall",
            "Idli sambhar breakfast",
            "Zomato order - butter chicken",
            "Swiggy - masala dosa",
            "Cold coffee at Cafe Coffee Day",
            "Vada pav snack",
            "Thali at Shanti Sagar",
            "Evening chai at Irani cafe",
        ],
    ),
    "Transport": (
        20, 500,
        [
            "Auto rickshaw to station",
            "Uber to office",
            "Ola cab ride",
            "Metro card recharge",
            "Petrol for bike",
            "BMTC bus pass",
            "Rapido bike ride",
            "Local train ticket",
            "Diesel for car",
            "Parking charges at mall",
            "Auto from airport",
        ],
    ),
    "Bills": (
        200, 3000,
        [
            "Jio postpaid bill",
            "Airtel broadband",
            "Tata Power electricity bill",
            "BSNL landline",
            "DTH recharge - Tata Play",
            "Gas cylinder refill",
            "Water tanker",
            "Maintenance charge - apartment",
            "Insurance premium - LIC",
            "Netflix subscription",
            "Spotify Premium",
            "Hotstar subscription",
        ],
    ),
    "Health": (
        100, 2000,
        [
            "Apollo Pharmacy medicines",
            "Doctor consultation - Practo",
            "Lab test - Thyrocare",
            "Dental cleaning",
            "Eye checkup at Sankara",
            "Pharmacy - cold and flu",
            "Vitamins and supplements",
            "Health checkup package",
            "Ayurvedic massage",
            "First aid supplies",
        ],
    ),
    "Entertainment": (
        100, 1500,
        [
            "PVR movie tickets",
            "BookMyShow - concert",
            "IPL match ticket",
            "Amazon Prime renewal",
            "Disney+ Hotstar",
            "Board game cafe",
            "Bowling at Smaaash",
            "Stand-up comedy show",
            "Museum entry - Chhatrapati Shivaji Maharaj Vastu",
            "Amusement park entry",
        ],
    ),
    "Shopping": (
        200, 5000,
        [
            "Flipkart - mobile cover",
            "Amazon - kitchen utensils",
            "Myntra - kurta",
            "Ajio - jeans",
            "Decathlon - sports shoes",
            "Big Bazaar groceries",
            "Reliance Digital - earphones",
            "Croma - small appliance",
            "Local tailor - shirt stitching",
            "DMart - monthly groceries",
            "Westside - casual wear",
        ],
    ),
    "Other": (
        50, 1000,
        [
            "Barber shop haircut",
            "Laundry - dhobi",
            "Stationery at shop",
            "Postage stamps",
            "Key duplicate",
            "Watch battery replacement",
            "Gift wrap and card",
            "Donation at temple",
            "Photocopying and printing",
            "House help bonus",
        ],
    ),
}

# Proportional weights: Food most common, Health/Entertainment least.
WEIGHTS = {
    "Food": 0.28,
    "Transport": 0.18,
    "Shopping": 0.16,
    "Bills": 0.14,
    "Other": 0.10,
    "Health": 0.07,
    "Entertainment": 0.07,
}


def random_date_within_months(months: int) -> date:
    """Pick a random date between today and `months` months ago (inclusive)."""
    end = date.today()
    start = end - timedelta(days=months * 30)
    delta_days = (end - start).days
    return start + timedelta(days=random.randint(0, delta_days))


def pick_category() -> str:
    categories = list(WEIGHTS.keys())
    weights = list(WEIGHTS.values())
    return random.choices(categories, weights=weights, k=1)[0]


def seed_expenses(user_id: int, count: int, months: int) -> list[dict]:
    """Insert `count` expenses for `user_id` across the last `months` months.

    Returns a list of inserted-row dicts. All inserts happen in a single
    transaction; any failure rolls back the whole batch.
    """
    conn = get_db()
    inserted: list[dict] = []
    try:
        for _ in range(count):
            category = pick_category()
            low, high, descriptions = CATEGORIES[category]
            amount = round(random.uniform(low, high), 2)
            description = random.choice(descriptions)
            d = random_date_within_months(months)

            cur = conn.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, amount, category, d.isoformat(), description),
            )
            inserted.append(
                {
                    "id": cur.lastrowid,
                    "amount": amount,
                    "category": category,
                    "date": d.isoformat(),
                    "description": description,
                }
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return inserted


def main() -> int:
    if len(sys.argv) != 4:
        print("Usage: python seed_expenses.py <user_id> <count> <months>")
        return 1
    try:
        user_id = int(sys.argv[1])
        count = int(sys.argv[2])
        months = int(sys.argv[3])
    except ValueError:
        print("user_id, count, and months must all be integers.")
        return 1

    conn = get_db()
    try:
        user = conn.execute(
            "SELECT id, name, email FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()
    if user is None:
        print(f"No user found with id {user_id}.")
        return 1

    print(f"Seeding {count} expenses for user {user['id']} ({user['email']}) "
          f"across the last {months} months...\n")
    inserted = seed_expenses(user_id, count, months)

    print(f"Inserted: {len(inserted)} expenses")
    if inserted:
        dates = sorted(r["date"] for r in inserted)
        print(f"Date range: {dates[0]}  to  {dates[-1]}")
        print("\nSample of 5 inserted records:")
        for row in random.sample(inserted, k=min(5, len(inserted))):
            print(
                f"  id={row['id']:>4}  {row['date']}  {row['category']:<14} "
                f"Rs.{row['amount']:>8.2f}  - {row['description']}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
