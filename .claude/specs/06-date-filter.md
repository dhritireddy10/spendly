# Spec: Date Filter

## Overview
Step 6 adds a date-range filter to the `/profile` page so a user can narrow the
recent transactions list, summary stats, and category breakdown down to a
specific time window (e.g. this month, last 30 days, or a custom range),
instead of always seeing all-time data. This builds directly on the live
database queries wired up in Step 5, extending each query helper to accept
optional date bounds.

## Depends on
- Step 1: Database setup (tables and `get_db()` exist)
- Step 3: Login / Logout (`session["user_id"]` is set on login)
- Step 5: Backend connection (`database/queries.py` helpers already query live
  data for stats, transactions, and category breakdown)

## Routes
- `GET /profile` — modified — logged-in — now accepts optional `start_date`
  and `end_date` query string parameters (`YYYY-MM-DD`) and applies them to
  stats, transactions, and category breakdown. No new route is created.

If no `start_date`/`end_date` are supplied, behavior is unchanged (all-time
data, matching Step 5).

## Database changes
No database changes. The `expenses.date` column (`TEXT`, ISO `YYYY-MM-DD`)
already supports lexicographic range comparisons with `?` placeholders.

## Templates
- **Modify:** `templates/profile.html`
  - Add a small filter form (date range inputs + submit) above the summary
    stats section, using `GET` so the range persists in the URL.
  - Inputs use `<input type="date">`, pre-filled from the current
    `start_date`/`end_date` query params via `request.args` passed into the
    template.
  - Add a "Clear filter" link (via `url_for('profile')` with no query args)
    shown only when a filter is active.

## Files to change
- `app.py` — `profile()` reads `start_date`/`end_date` from `request.args`
  and passes them through to the query helpers
- `database/queries.py` — `get_summary_stats`, `get_recent_transactions`,
  `get_category_breakdown` each gain optional `start_date=None, end_date=None`
  params and append `AND date >= ?` / `AND date <= ?` clauses when provided
- `templates/profile.html` — add the filter form and "Clear filter" link
- `static/css/profile.css` — style the new filter form using existing CSS
  variables

## Files to create
No new files.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL, including
  the new date bounds
- Foreign keys PRAGMA must be enabled on every connection (already done in
  `get_db()`)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- Currency must always display as ₹ — never £ or $
- Invalid or malformed date input (e.g. `end_date` before `start_date`,
  unparseable strings) must be ignored gracefully — fall back to no filter for
  that bound rather than raising an exception
- Query helpers must remain pure (no Flask imports) and continue to call
  `get_db()` internally, closing the connection before returning

## Definition of done
- [ ] Visiting `/profile` with no query params shows all-time data, identical
      to current behavior
- [ ] Submitting a date range (e.g. last 7 days) updates total spent,
      transaction count, top category, transaction list, and category
      breakdown to reflect only expenses within that range
- [ ] The date inputs remain pre-filled with the submitted range after the
      page reloads
- [ ] A "Clear filter" link appears only when a filter is active, and clicking
      it returns to the all-time view
- [ ] Selecting a range with zero matching expenses shows ₹0.00 total spent,
      0 transactions, and an empty category breakdown — no errors
- [ ] Submitting an `end_date` earlier than `start_date` does not crash the
      page
