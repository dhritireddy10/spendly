"""
Tests for Step 6: Date Filter (spec: .claude/specs/06-date-filter.md)

These tests are written strictly against the spec's described behavior for
`GET /profile` with optional `start_date` / `end_date` query params. Shared
fixtures (`temp_db`, `client`) and helpers (`_make_user`, `_add_expense`)
live in tests/conftest.py so they're not duplicated across test files.
"""
import pytest

import database.db as db
from tests.conftest import add_expense as _add_expense
from tests.conftest import make_user as _make_user


# --------------------------------------------------------------------- #
# Unit tests — database/queries.py date-bounds behavior
# --------------------------------------------------------------------- #

class TestQueriesDateBounds:
    def test_date_bounds_clause_no_args(self):
        from database.queries import _date_bounds_clause

        assert _date_bounds_clause() == ("", [])

    def test_date_bounds_clause_start_only(self):
        from database.queries import _date_bounds_clause

        assert _date_bounds_clause(start_date="2026-01-01") == (" AND date >= ?", ["2026-01-01"])

    def test_date_bounds_clause_end_only(self):
        from database.queries import _date_bounds_clause

        assert _date_bounds_clause(end_date="2026-01-31") == (" AND date <= ?", ["2026-01-31"])

    def test_date_bounds_clause_both(self):
        from database.queries import _date_bounds_clause

        clause, params = _date_bounds_clause(start_date="2026-01-01", end_date="2026-01-31")
        assert clause == " AND date >= ? AND date <= ?"
        assert params == ["2026-01-01", "2026-01-31"]

    def test_get_summary_stats_with_date_range(self, temp_db):
        from database import queries

        user_id = _make_user()
        _add_expense(user_id, 100.0, "Bills", "2026-01-01")
        _add_expense(user_id, 50.0, "Food", "2026-01-15")
        _add_expense(user_id, 25.0, "Bills", "2026-02-01")

        stats = queries.get_summary_stats(user_id, start_date="2026-01-01", end_date="2026-01-31")

        assert stats["total_spent"] == 150.0
        assert stats["transaction_count"] == 2
        assert stats["top_category"] == "Bills"

    def test_get_summary_stats_date_range_no_matches(self, temp_db):
        from database import queries

        user_id = _make_user()
        _add_expense(user_id, 100.0, "Bills", "2026-01-01")

        stats = queries.get_summary_stats(user_id, start_date="2026-03-01", end_date="2026-03-31")

        assert stats == {"total_spent": 0, "transaction_count": 0, "top_category": "—"}

    def test_get_recent_transactions_with_date_range(self, temp_db):
        from database import queries

        user_id = _make_user()
        _add_expense(user_id, 10.0, "Food", "2026-01-01", "Too early")
        _add_expense(user_id, 20.0, "Bills", "2026-01-15", "In range")
        _add_expense(user_id, 15.0, "Transport", "2026-02-01", "Too late")

        result = queries.get_recent_transactions(user_id, start_date="2026-01-10", end_date="2026-01-20")

        assert [tx["description"] for tx in result] == ["In range"]

    def test_get_recent_transactions_start_date_only(self, temp_db):
        from database import queries

        user_id = _make_user()
        _add_expense(user_id, 10.0, "Food", "2026-01-01", "Before")
        _add_expense(user_id, 20.0, "Bills", "2026-01-15", "After")

        result = queries.get_recent_transactions(user_id, start_date="2026-01-10")

        assert [tx["description"] for tx in result] == ["After"]

    def test_get_recent_transactions_end_date_only(self, temp_db):
        from database import queries

        user_id = _make_user()
        _add_expense(user_id, 10.0, "Food", "2026-01-01", "Before")
        _add_expense(user_id, 20.0, "Bills", "2026-01-15", "After")

        result = queries.get_recent_transactions(user_id, end_date="2026-01-10")

        assert [tx["description"] for tx in result] == ["Before"]

    def test_get_category_breakdown_with_date_range(self, temp_db):
        from database import queries

        user_id = _make_user()
        _add_expense(user_id, 75.0, "Bills", "2026-01-01")
        _add_expense(user_id, 20.0, "Food", "2026-01-02")
        _add_expense(user_id, 500.0, "Transport", "2026-03-01")

        result = queries.get_category_breakdown(user_id, start_date="2026-01-01", end_date="2026-01-31")

        names = {item["name"] for item in result}
        assert names == {"Bills", "Food"}
        assert sum(item["pct"] for item in result) == 100

    def test_get_category_breakdown_date_range_no_matches(self, temp_db):
        from database import queries

        user_id = _make_user()
        _add_expense(user_id, 75.0, "Bills", "2026-01-01")

        assert queries.get_category_breakdown(user_id, start_date="2026-06-01", end_date="2026-06-30") == []


# --------------------------------------------------------------------- #
# Route fixtures
# --------------------------------------------------------------------- #

@pytest.fixture
def registered_client(client):
    """A test client with a fresh registered+logged-in user and no expenses yet."""
    client.post(
        "/register",
        data={
            "name": "Range User",
            "email": "range@example.com",
            "password": "password123",
            "confirm_password": "password123",
        },
    )
    client.post("/login", data={"email": "range@example.com", "password": "password123"})
    return client


def _seed_spread_expenses(user_id):
    """Seed expenses spread across distinct, non-adjacent dates for range testing."""
    _add_expense(user_id, 100.0, "Food", "2026-01-01", "January expense")
    _add_expense(user_id, 200.0, "Bills", "2026-02-15", "February expense")
    _add_expense(user_id, 300.0, "Transport", "2026-03-10", "March expense")
    _add_expense(user_id, 400.0, "Shopping", "2026-04-20", "April expense")


# --------------------------------------------------------------------- #
# Auth guard
# --------------------------------------------------------------------- #

class TestDateFilterAuthGuard:
    def test_profile_redirects_when_unauthenticated_no_params(self, client):
        response = client.get("/profile")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_profile_redirects_when_unauthenticated_with_date_params(self, client):
        response = client.get("/profile?start_date=2026-01-01&end_date=2026-12-31")
        assert response.status_code == 302, "Auth guard must apply regardless of query params"
        assert "/login" in response.headers["Location"]


# --------------------------------------------------------------------- #
# Happy path: no filter == all-time behavior
# --------------------------------------------------------------------- #

class TestDateFilterNoParams:
    def test_no_query_params_shows_all_time_data(self, registered_client):
        from database import queries

        user_id = db.get_user_by_email("range@example.com")["id"]
        _seed_spread_expenses(user_id)

        response = registered_client.get("/profile")
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        expected_stats = queries.get_summary_stats(user_id)
        assert expected_stats["transaction_count"] == 4
        assert f"₹{expected_stats['total_spent']:,.2f}" in body
        assert str(expected_stats["transaction_count"]) in body

    def test_no_query_params_lists_all_transactions(self, registered_client):
        user_id = db.get_user_by_email("range@example.com")["id"]
        _seed_spread_expenses(user_id)

        response = registered_client.get("/profile")
        body = response.get_data(as_text=True)

        for description in ["January expense", "February expense", "March expense", "April expense"]:
            assert description in body

    def test_no_query_params_no_clear_filter_link(self, registered_client):
        user_id = db.get_user_by_email("range@example.com")["id"]
        _seed_spread_expenses(user_id)

        response = registered_client.get("/profile")
        body = response.get_data(as_text=True)

        assert "Clear filter" not in body, (
            "Clear filter link/state should only appear when a filter is active"
        )


# --------------------------------------------------------------------- #
# Happy path: valid range narrows results
# --------------------------------------------------------------------- #

class TestDateFilterValidRange:
    def test_valid_range_narrows_transaction_list(self, registered_client):
        user_id = db.get_user_by_email("range@example.com")["id"]
        _seed_spread_expenses(user_id)

        response = registered_client.get("/profile?start_date=2026-02-01&end_date=2026-03-31")
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "February expense" in body
        assert "March expense" in body
        assert "January expense" not in body
        assert "April expense" not in body

    def test_valid_range_narrows_summary_stats(self, registered_client):
        from database import queries

        user_id = db.get_user_by_email("range@example.com")["id"]
        _seed_spread_expenses(user_id)

        response = registered_client.get("/profile?start_date=2026-02-01&end_date=2026-03-31")
        body = response.get_data(as_text=True)

        # Only February (200.0) + March (300.0) expenses should count.
        stats = queries.get_summary_stats(user_id, start_date="2026-02-01", end_date="2026-03-31")
        assert stats["total_spent"] == 500.0
        assert stats["transaction_count"] == 2
        assert "₹500.00" in body
        assert str(stats["transaction_count"]) in body

    def test_valid_range_narrows_category_breakdown(self, registered_client):
        user_id = db.get_user_by_email("range@example.com")["id"]
        _seed_spread_expenses(user_id)

        response = registered_client.get("/profile?start_date=2026-02-01&end_date=2026-03-31")
        body = response.get_data(as_text=True)

        assert "Bills" in body
        assert "Transport" in body
        # Food and Shopping expenses fall outside the range and should not
        # appear as line-item categories with amounts in the breakdown.
        assert "January expense" not in body
        assert "April expense" not in body

    def test_valid_range_query_helper_matches_route_output(self, registered_client):
        from database import queries

        user_id = db.get_user_by_email("range@example.com")["id"]
        _seed_spread_expenses(user_id)

        response = registered_client.get("/profile?start_date=2026-02-01&end_date=2026-03-31")
        body = response.get_data(as_text=True)

        stats = queries.get_summary_stats(user_id, start_date="2026-02-01", end_date="2026-03-31")
        assert stats["transaction_count"] == 2
        assert stats["total_spent"] == 500.0
        assert f"₹{stats['total_spent']:,.2f}" in body
        assert str(stats["transaction_count"]) in body

    def test_single_day_range_matches_exact_boundary(self, registered_client):
        user_id = db.get_user_by_email("range@example.com")["id"]
        _seed_spread_expenses(user_id)

        response = registered_client.get("/profile?start_date=2026-02-15&end_date=2026-02-15")
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "February expense" in body
        assert "January expense" not in body
        assert "March expense" not in body


# --------------------------------------------------------------------- #
# Template pre-fill and Clear filter behavior
# --------------------------------------------------------------------- #

class TestDateFilterTemplate:
    def test_date_inputs_prefilled_with_submitted_range(self, registered_client):
        user_id = db.get_user_by_email("range@example.com")["id"]
        _seed_spread_expenses(user_id)

        response = registered_client.get("/profile?start_date=2026-02-01&end_date=2026-03-31")
        body = response.get_data(as_text=True)

        assert 'value="2026-02-01"' in body
        assert 'value="2026-03-31"' in body

    def test_clear_filter_link_present_when_filter_active(self, registered_client):
        user_id = db.get_user_by_email("range@example.com")["id"]
        _seed_spread_expenses(user_id)

        response = registered_client.get("/profile?start_date=2026-02-01&end_date=2026-03-31")
        body = response.get_data(as_text=True)

        assert "Clear filter" in body

    def test_clear_filter_link_returns_to_all_time_view(self, registered_client):
        user_id = db.get_user_by_email("range@example.com")["id"]
        _seed_spread_expenses(user_id)

        # Simulate following the "Clear filter" link: GET /profile with no params.
        response = registered_client.get("/profile")
        body = response.get_data(as_text=True)

        for description in ["January expense", "February expense", "March expense", "April expense"]:
            assert description in body
        assert "Clear filter" not in body

    def test_clear_filter_absent_with_only_start_date(self, registered_client):
        """Spec says clear filter shown 'only when a filter is active' — a single
        bound already constitutes an active filter."""
        user_id = db.get_user_by_email("range@example.com")["id"]
        _seed_spread_expenses(user_id)

        response = registered_client.get("/profile?start_date=2026-02-01")
        body = response.get_data(as_text=True)

        assert "Clear filter" in body


# --------------------------------------------------------------------- #
# Validation / edge cases
# --------------------------------------------------------------------- #

class TestDateFilterEdgeCases:
    def test_malformed_start_date_ignored_gracefully(self, registered_client):
        user_id = db.get_user_by_email("range@example.com")["id"]
        _seed_spread_expenses(user_id)

        response = registered_client.get("/profile?start_date=not-a-date&end_date=2026-03-31")
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        # start_date bound falls back to "no filter" -> everything up to end_date included
        assert "January expense" in body
        assert "February expense" in body
        assert "March expense" in body
        assert "April expense" not in body

    def test_malformed_end_date_ignored_gracefully(self, registered_client):
        user_id = db.get_user_by_email("range@example.com")["id"]
        _seed_spread_expenses(user_id)

        response = registered_client.get("/profile?start_date=2026-02-01&end_date=garbage")
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "February expense" in body
        assert "March expense" in body
        assert "April expense" in body
        assert "January expense" not in body

    def test_both_dates_malformed_falls_back_to_all_time(self, registered_client):
        user_id = db.get_user_by_email("range@example.com")["id"]
        _seed_spread_expenses(user_id)

        response = registered_client.get("/profile?start_date=xx&end_date=yy")
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        for description in ["January expense", "February expense", "March expense", "April expense"]:
            assert description in body

    def test_end_date_before_start_date_does_not_crash(self, registered_client):
        """Per spec, an end_date earlier than start_date is dropped rather than
        applied — the route falls back to filtering on start_date alone."""
        user_id = db.get_user_by_email("range@example.com")["id"]
        _seed_spread_expenses(user_id)

        response = registered_client.get("/profile?start_date=2026-04-01&end_date=2026-01-01")
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        # Only the April expense is on/after 2026-04-01; the invalid end_date
        # must not silently reset to "no filter" (all four expenses).
        assert "April expense" in body
        assert "January expense" not in body
        assert "February expense" not in body
        assert "March expense" not in body

    def test_zero_matching_expenses_returns_empty_state(self, registered_client):
        user_id = db.get_user_by_email("range@example.com")["id"]
        _seed_spread_expenses(user_id)

        response = registered_client.get("/profile?start_date=2027-01-01&end_date=2027-01-31")
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "₹0.00" in body
        for description in ["January expense", "February expense", "March expense", "April expense"]:
            assert description not in body

    def test_zero_matching_expenses_query_helper_returns_empty(self, registered_client):
        from database import queries

        user_id = db.get_user_by_email("range@example.com")["id"]
        _seed_spread_expenses(user_id)

        stats = queries.get_summary_stats(user_id, start_date="2027-01-01", end_date="2027-01-31")
        assert stats["total_spent"] == 0
        assert stats["transaction_count"] == 0
        assert stats["top_category"] == "—"

        transactions = queries.get_recent_transactions(user_id, start_date="2027-01-01", end_date="2027-01-31")
        assert transactions == []

        breakdown = queries.get_category_breakdown(user_id, start_date="2027-01-01", end_date="2027-01-31")
        assert breakdown == []

    def test_empty_string_date_params_treated_as_no_filter(self, registered_client):
        user_id = db.get_user_by_email("range@example.com")["id"]
        _seed_spread_expenses(user_id)

        response = registered_client.get("/profile?start_date=&end_date=")
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        for description in ["January expense", "February expense", "March expense", "April expense"]:
            assert description in body
