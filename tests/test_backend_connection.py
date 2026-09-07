from tests.conftest import add_expense as _add_expense
from tests.conftest import make_user as _make_user


# --------------------------------------------------------------------- #
# Unit tests — database/queries.py
# --------------------------------------------------------------------- #

def test_get_user_by_id_valid(temp_db):
    from database import queries

    user_id = _make_user()
    result = queries.get_user_by_id(user_id)

    assert result["name"] == "Test User"
    assert result["email"] == "test@example.com"
    assert result["member_since"]  # e.g. "September 2026"


def test_get_user_by_id_missing(temp_db):
    from database import queries

    assert queries.get_user_by_id(9999) is None


def test_get_summary_stats_with_expenses(temp_db):
    from database import queries

    user_id = _make_user()
    _add_expense(user_id, 100.0, "Bills", "2026-01-05")
    _add_expense(user_id, 50.0, "Food", "2026-01-06")
    _add_expense(user_id, 25.0, "Bills", "2026-01-07")

    stats = queries.get_summary_stats(user_id)

    assert stats["total_spent"] == 175.0
    assert stats["transaction_count"] == 3
    assert stats["top_category"] == "Bills"


def test_get_summary_stats_no_expenses(temp_db):
    from database import queries

    user_id = _make_user()
    stats = queries.get_summary_stats(user_id)

    assert stats == {"total_spent": 0, "transaction_count": 0, "top_category": "—"}


def test_get_recent_transactions_with_expenses(temp_db):
    from database import queries

    user_id = _make_user()
    _add_expense(user_id, 10.0, "Food", "2026-01-01", "Old")
    _add_expense(user_id, 20.0, "Bills", "2026-01-03", "Newest")
    _add_expense(user_id, 15.0, "Transport", "2026-01-02", "Middle")

    result = queries.get_recent_transactions(user_id)

    assert [tx["description"] for tx in result] == ["Newest", "Middle", "Old"]
    for tx in result:
        assert set(tx.keys()) >= {"date", "description", "category", "amount"}


def test_get_recent_transactions_no_expenses(temp_db):
    from database import queries

    user_id = _make_user()
    assert queries.get_recent_transactions(user_id) == []


def test_get_category_breakdown_with_expenses(temp_db):
    from database import queries

    user_id = _make_user()
    _add_expense(user_id, 75.0, "Bills", "2026-01-01")
    _add_expense(user_id, 20.0, "Food", "2026-01-02")
    _add_expense(user_id, 5.0, "Transport", "2026-01-03")

    result = queries.get_category_breakdown(user_id)

    amounts = [item["amount"] for item in result]
    assert amounts == sorted(amounts, reverse=True)

    for item in result:
        assert isinstance(item["pct"], int)
    assert sum(item["pct"] for item in result) == 100


def test_get_category_breakdown_no_expenses(temp_db):
    from database import queries

    user_id = _make_user()
    assert queries.get_category_breakdown(user_id) == []


# --------------------------------------------------------------------- #
# Route tests — GET /profile
# --------------------------------------------------------------------- #

def test_profile_redirects_when_unauthenticated(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_profile_authenticated_seed_user(client):
    login_response = client.post(
        "/login",
        data={"email": "demo@spendly.com", "password": "demo123"},
        follow_redirects=True,
    )
    assert login_response.status_code == 200

    response = client.get("/profile")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Demo User" in body
    assert "demo@spendly.com" in body
    assert "₹" in body

    from database import queries

    expected_stats = queries.get_summary_stats(1)
    assert f"₹{expected_stats['total_spent']:,.2f}" in body
    assert str(expected_stats["transaction_count"]) in body
    assert expected_stats["top_category"] in body

    date_idx = body.index("Recent transactions")
    dates_section = body[date_idx:date_idx + 4000]
    assert dates_section  # transaction rows render after the section heading

    for category in ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]:
        assert category in body


def test_profile_new_user_has_no_expenses(client):
    client.post(
        "/register",
        data={
            "name": "Fresh User",
            "email": "fresh@example.com",
            "password": "password123",
            "confirm_password": "password123",
        },
    )
    client.post("/login", data={"email": "fresh@example.com", "password": "password123"})

    response = client.get("/profile")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "₹0.00" in body
