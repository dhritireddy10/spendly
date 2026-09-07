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


def _make_user(name="Test User", email="test@example.com", password="password123"):
    return db.create_user(name, email, password)


def _add_expense(user_id, amount, category, date, description=""):
    conn = db.get_db()
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, date, description),
    )
    conn.commit()
    conn.close()


# --------------------------------------------------------------------- #
# Unit tests — database/queries.py
# --------------------------------------------------------------------- #

def test_date_bounds_clause_no_args():
    from database.queries import _date_bounds_clause

    assert _date_bounds_clause() == ("", [])


def test_date_bounds_clause_start_only():
    from database.queries import _date_bounds_clause

    assert _date_bounds_clause(start_date="2026-01-01") == (" AND date >= ?", ["2026-01-01"])


def test_date_bounds_clause_end_only():
    from database.queries import _date_bounds_clause

    assert _date_bounds_clause(end_date="2026-01-31") == (" AND date <= ?", ["2026-01-31"])


def test_date_bounds_clause_both():
    from database.queries import _date_bounds_clause

    clause, params = _date_bounds_clause(start_date="2026-01-01", end_date="2026-01-31")
    assert clause == " AND date >= ? AND date <= ?"
    assert params == ["2026-01-01", "2026-01-31"]


def test_get_summary_stats_with_date_range(temp_db):
    from database import queries

    user_id = _make_user()
    _add_expense(user_id, 100.0, "Bills", "2026-01-01")
    _add_expense(user_id, 50.0, "Food", "2026-01-15")
    _add_expense(user_id, 25.0, "Bills", "2026-02-01")

    stats = queries.get_summary_stats(user_id, start_date="2026-01-01", end_date="2026-01-31")

    assert stats["total_spent"] == 150.0
    assert stats["transaction_count"] == 2
    assert stats["top_category"] == "Bills"


def test_get_summary_stats_date_range_no_matches(temp_db):
    from database import queries

    user_id = _make_user()
    _add_expense(user_id, 100.0, "Bills", "2026-01-01")

    stats = queries.get_summary_stats(user_id, start_date="2026-03-01", end_date="2026-03-31")

    assert stats == {"total_spent": 0, "transaction_count": 0, "top_category": "—"}


def test_get_recent_transactions_with_date_range(temp_db):
    from database import queries

    user_id = _make_user()
    _add_expense(user_id, 10.0, "Food", "2026-01-01", "Too early")
    _add_expense(user_id, 20.0, "Bills", "2026-01-15", "In range")
    _add_expense(user_id, 15.0, "Transport", "2026-02-01", "Too late")

    result = queries.get_recent_transactions(user_id, start_date="2026-01-10", end_date="2026-01-20")

    assert [tx["description"] for tx in result] == ["In range"]


def test_get_recent_transactions_start_date_only(temp_db):
    from database import queries

    user_id = _make_user()
    _add_expense(user_id, 10.0, "Food", "2026-01-01", "Before")
    _add_expense(user_id, 20.0, "Bills", "2026-01-15", "After")

    result = queries.get_recent_transactions(user_id, start_date="2026-01-10")

    assert [tx["description"] for tx in result] == ["After"]


def test_get_recent_transactions_end_date_only(temp_db):
    from database import queries

    user_id = _make_user()
    _add_expense(user_id, 10.0, "Food", "2026-01-01", "Before")
    _add_expense(user_id, 20.0, "Bills", "2026-01-15", "After")

    result = queries.get_recent_transactions(user_id, end_date="2026-01-10")

    assert [tx["description"] for tx in result] == ["Before"]


def test_get_category_breakdown_with_date_range(temp_db):
    from database import queries

    user_id = _make_user()
    _add_expense(user_id, 75.0, "Bills", "2026-01-01")
    _add_expense(user_id, 20.0, "Food", "2026-01-02")
    _add_expense(user_id, 500.0, "Transport", "2026-03-01")

    result = queries.get_category_breakdown(user_id, start_date="2026-01-01", end_date="2026-01-31")

    names = {item["name"] for item in result}
    assert names == {"Bills", "Food"}
    assert sum(item["pct"] for item in result) == 100


def test_get_category_breakdown_date_range_no_matches(temp_db):
    from database import queries

    user_id = _make_user()
    _add_expense(user_id, 75.0, "Bills", "2026-01-01")

    assert queries.get_category_breakdown(user_id, start_date="2026-06-01", end_date="2026-06-30") == []


# --------------------------------------------------------------------- #
# Route tests — GET /profile with date filters
# --------------------------------------------------------------------- #

@pytest.fixture
def client(tmp_path, monkeypatch):
    """Build a Flask test client backed by a fresh, seeded temp database."""
    db_path = tmp_path / "test_spendly_app.db"
    monkeypatch.setattr(db, "DB_PATH", str(db_path))

    for mod_name in ("database.queries", "app"):
        sys.modules.pop(mod_name, None)

    app_module = importlib.import_module("app")
    app_module.app.config.update(TESTING=True)

    with app_module.app.test_client() as test_client:
        yield test_client


def _login(client):
    client.post(
        "/login",
        data={"email": "demo@spendly.com", "password": "demo123"},
        follow_redirects=True,
    )


def test_profile_with_valid_date_range_filters_data(client):
    _login(client)

    from database import queries

    start_date, end_date = "2026-01-01", "2026-12-31"
    expected_stats = queries.get_summary_stats(1, start_date=start_date, end_date=end_date)

    response = client.get(f"/profile?start_date={start_date}&end_date={end_date}")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert f"₹{expected_stats['total_spent']:,.2f}" in body
    assert str(expected_stats["transaction_count"]) in body


def test_profile_date_inputs_prefilled(client):
    _login(client)

    response = client.get("/profile?start_date=2026-01-01&end_date=2026-01-31")
    body = response.get_data(as_text=True)

    assert 'value="2026-01-01"' in body
    assert 'value="2026-01-31"' in body


def test_profile_clear_filter_link_appears_only_when_filtered(client):
    _login(client)

    unfiltered = client.get("/profile").get_data(as_text=True)
    assert "Clear filter" not in unfiltered

    filtered = client.get("/profile?start_date=2026-01-01").get_data(as_text=True)
    assert "Clear filter" in filtered


def test_profile_zero_match_range_shows_empty_state(client):
    _login(client)

    response = client.get("/profile?start_date=2020-01-01&end_date=2020-01-31")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "₹0.00" in body


def test_profile_invalid_end_before_start_does_not_crash(client):
    _login(client)

    response = client.get("/profile?start_date=2026-02-01&end_date=2026-01-01")

    assert response.status_code == 200


def test_profile_malformed_date_ignored(client):
    _login(client)

    unfiltered = client.get("/profile").get_data(as_text=True)
    malformed = client.get("/profile?start_date=not-a-date").get_data(as_text=True)

    assert malformed == unfiltered
