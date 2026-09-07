import importlib
import sys

import pytest

import database.db as db


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point database.db (and everything importing get_db from it) at a fresh sqlite file."""
    db_path = tmp_path / "test_spendly.db"
    monkeypatch.setattr(db, "DB_PATH", str(db_path))
    db.init_db()
    return db_path


def make_user(name="Test User", email="test@example.com", password="password123"):
    return db.create_user(name, email, password)


def add_expense(user_id, amount, category, date, description=""):
    conn = db.get_db()
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, date, description),
    )
    conn.commit()
    conn.close()


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Build a Flask test client backed by a fresh temp database.

    Note: app.py seeds a "Demo User" (id 1, demo@spendly.com) and sample
    expenses at import time via seed_db() — this fixture does not disable
    that, it only points the database at an isolated temp file per test.
    """
    db_path = tmp_path / "test_spendly_app.db"
    monkeypatch.setattr(db, "DB_PATH", str(db_path))

    # database.queries and app both cache references resolved at import time
    # (e.g. via `from database.db import get_db`), so they must be re-imported
    # after DB_PATH changes for the new path to actually take effect.
    for mod_name in ("database.queries", "app"):
        sys.modules.pop(mod_name, None)

    app_module = importlib.import_module("app")
    app_module.app.config.update(TESTING=True)

    with app_module.app.test_client() as test_client:
        yield test_client
