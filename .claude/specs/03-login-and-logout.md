# Spec: Login and Logout

## Overview
This feature implements session-based authentication for Spendly. It turns the existing `GET /login` page into a working sign-in flow that validates credentials against the `users` table, establishes a Flask session on success, and adds a `GET /logout` route that clears that session. On success, login redirects back to the landing page (`/`), which shows a personalized "Welcome back, {name}!" greeting in place of the marketing badge when a session is active — `/profile` itself remains an unbuilt stub until Step 4. This is the step that makes "logged-in" a real concept in the app, unblocking `/profile` and the expense routes (Steps 4, 7, 8, 9), which will depend on a logged-in user existing in the session.

## Depends on
- Step 01 — Database setup (`users` table, `get_db()`)
- Step 02 — Registration (`create_user`, `get_user_by_email`, password hashing with werkzeug)

## Routes
- `POST /login` — validate email/password against `users`, start session, redirect to `/` (landing page) — public
- `GET /login` — already implemented, renders `login.html` — public (no change needed, but must redirect to `/` if already logged in)
- `GET /logout` — clear the session, redirect to `/login` — logged-in only (a logged-out visitor is simply redirected to `/login` with no error)
- `GET /` — already implemented, renders `landing.html` — public (no change to access level, but now looks up the current user via session and passes it to the template for the "Welcome back" greeting)

## Database changes
No database changes. `users` table, `get_user_by_email()`, and the new `get_user_by_id()` (see below) all live in `database/db.py`.

## Templates
- **Create:** none
- **Modify:**
  - `templates/login.html` — no structural change needed; it already posts to `/login` and renders `{{ error }}`.
  - `templates/base.html` — nav links currently hardcode "Sign in" / "Get started" regardless of auth state; update to show "Profile" / "Logout" when `session.get('user_id')` is set, and "Sign in" / "Get started" otherwise.
  - `templates/landing.html` — the hero badge shows "Welcome back, {{ user.name }}!" when a `user` is passed in (logged in), otherwise the existing "Free to use · No credit card needed" badge.

## Files to change
- `app.py` — add `POST` handling to `/login` (redirecting to `/` on success), implement `/logout`, update the `landing` route to look up the current user from the session and pass it to `landing.html`
- `database/db.py` — add `get_user_by_id(user_id)` helper, used by the `landing` route to fetch the display name for the welcome message
- `templates/base.html` — conditional nav links based on session
- `templates/landing.html` — conditional "Welcome back" greeting based on session

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
- [ ] Visiting `/login` and submitting valid demo credentials (`demo@spendly.com` / `demo123`) redirects to `/`, and the landing page shows "Welcome back, Demo User!" in place of the marketing badge
- [ ] `/profile` remains an untouched stub (`Profile page — coming in Step 4`) and is not linked from the login success path
- [ ] Submitting an unknown email on `/login` re-renders the login page with an error, without revealing whether the email exists
- [ ] Submitting a known email with the wrong password re-renders the login page with a generic error
- [ ] After a successful login, visiting `/logout` clears the session and redirects to `/login`
- [ ] After logout, the nav bar shows "Sign in" / "Get started" again
- [ ] While logged in, the nav bar shows "Profile" / "Logout" instead of "Sign in" / "Get started"
- [ ] Visiting `/logout` while not logged in does not error — it redirects to `/login`
- [ ] No plaintext password ever appears in a log, session, or response
