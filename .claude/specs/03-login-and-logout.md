# Spec: Login and Logout

## Overview
This feature implements session-based authentication for Spendly. It turns the existing `GET /login` page into a working sign-in flow that validates credentials against the `users` table, establishes a Flask session on success, and adds a `GET /logout` route that clears that session. This is the step that makes "logged-in" a real concept in the app, unblocking `/profile` and the expense routes (Steps 4, 7, 8, 9), which will depend on a logged-in user existing in the session.

## Depends on
- Step 01 — Database setup (`users` table, `get_db()`)
- Step 02 — Registration (`create_user`, `get_user_by_email`, password hashing with werkzeug)

## Routes
- `POST /login` — validate email/password against `users`, start session, redirect to `/profile` — public
- `GET /login` — already implemented, renders `login.html` — public (no change needed, but must redirect to `/profile` if already logged in)
- `GET /logout` — clear the session, redirect to `/login` — logged-in only (a logged-out visitor is simply redirected to `/login` with no error)

## Database changes
No database changes. `users` table and `get_user_by_email()` already exist in `database/db.py`.

## Templates
- **Create:** none
- **Modify:** `templates/login.html` — no structural change needed; it already posts to `/login` and renders `{{ error }}`. `templates/base.html` — nav links currently hardcode "Sign in" / "Get started" regardless of auth state; update to show "Profile" / "Logout" when `session.get('user_id')` is set, and "Sign in" / "Get started" otherwise.

## Files to change
- `app.py` — add `POST` handling to `/login`, implement `/logout`, add a `login_required` check pattern for future protected routes (used starting Step 4)
- `database/db.py` — add `get_user_by_id(user_id)` helper (needed for future session-based lookups; not strictly required for login/logout itself, but establishes the pattern — only add if Step 4 is not immediately next; otherwise skip and let Step 4 add it)
- `templates/base.html` — conditional nav links based on session

## Files to create
None.

## New dependencies
No new dependencies. `werkzeug.security` (already used for `generate_password_hash`) provides `check_password_hash`.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug — use `check_password_hash` against `password_hash`, never compare plaintext
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Store only `user_id` in `session` (not the password hash or full row)
- Use `abort()` for HTTP errors, not bare string returns
- Do not touch `/profile` or any `/expenses/*` route — those stay stubs until their own steps
- Do not implement "remember me" or password reset — out of scope for this step

## Definition of done
- [ ] Visiting `/login` and submitting valid demo credentials (`demo@spendly.com` / `demo123`) redirects to `/profile`
- [ ] Submitting an unknown email on `/login` re-renders the login page with an error, without revealing whether the email exists
- [ ] Submitting a known email with the wrong password re-renders the login page with a generic error
- [ ] After a successful login, visiting `/logout` clears the session and redirects to `/login`
- [ ] After logout, the nav bar shows "Sign in" / "Get started" again
- [ ] While logged in, the nav bar shows "Profile" / "Logout" instead of "Sign in" / "Get started"
- [ ] Visiting `/logout` while not logged in does not error — it redirects to `/login`
- [ ] No plaintext password ever appears in a log, session, or response
