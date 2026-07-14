import os

import pytest

# spendly.db sits in the project root, same dir as this conftest.py.
DB_PATH = os.path.join(os.path.dirname(__file__), "spendly.db")


@pytest.fixture
def app():
    # Wipe any pre-existing DB so init_db/seed_db (which run on app import)
    # produce a clean, predictable fixture for every test.
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    from app import app as flask_app
    # app.py calls init_db() and seed_db() at import time, which built the
    # schema on the just-deleted file. We removed that file AFTER import, so
    # re-run the bootstrap to recreate the tables before any test request.
    from database.db import init_db, seed_db
    init_db()
    seed_db()

    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret"
    yield flask_app

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)


@pytest.fixture
def client(app):
    return app.test_client()
