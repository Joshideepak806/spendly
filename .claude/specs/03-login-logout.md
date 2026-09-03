# Spec: Login and Logout

## Overview
Turn the static `/login` page and the `/logout` placeholder into a working session flow. A visitor submits their email and password; the server looks the user up in the `users` table, verifies the password against the werkzeug hash written by Step 2, and stores the user's id and name in a signed Flask session. A logged-in user sees their name and a "Sign out" control in the navbar instead of "Sign in / Get started", and signing out clears the session. This step also introduces the `login_required` decorator that every later feature (profile, dashboard, expenses) depends on to know who the current user is.

## Depends on
- Step 1 — Database Setup (`users` table, `get_db()` in `database/db.py`)
- Step 2 — Registration (accounts exist with werkzeug password hashes; `/login?registered=1` success banner)

## Routes
- `GET /login` — render the sign-in form; redirect an already logged-in user to `/profile` — public
- `POST /login` — verify credentials, populate the session, redirect on success; re-render the form with an error on failure — public
- `POST /logout` — clear the session and redirect to `/` with a signed-out message — logged-in
- `GET /profile` — keep the Step 4 placeholder response, but only for logged-in users; anonymous visitors are redirected to `/login?next=/profile` — logged-in

Change the existing `@app.route("/login")` to `methods=["GET", "POST"]` and `@app.route("/logout")` to `methods=["POST"]`. `/logout` is POST-only on purpose: a `GET /logout` can be triggered by any third-party page embedding it as an image or link, silently signing the user out. No other routes change.

## Database changes
No database changes. Login is a read-only lookup: `SELECT id, name, password_hash FROM users WHERE email = ?`. The `users` table already has `email TEXT NOT NULL UNIQUE` and `password_hash TEXT NOT NULL`, which is everything this step needs. Do not add a sessions table — Flask's signed cookie session is the store.

## Templates
- **Create:** none
- **Modify:**
  - `templates/login.html` — point the form at `{{ url_for('login') }}` instead of the hardcoded `/login`; re-populate `email` on error (`value="{{ email or '' }}"`) and never re-populate the password; carry the `next` value through as a hidden input (`<input type="hidden" name="next" value="{{ next or '' }}">`). The existing `{% if error %}` / `{% if success %}` blocks already render `.auth-error` and `.auth-success`.
  - `templates/base.html` — make the navbar session-aware. When `session.get('user_id')` is set, show the user's name (`session.get('user_name')`) linking to `{{ url_for('profile') }}` plus a `POST` form to `{{ url_for('logout') }}` rendered as a button; otherwise keep the current "Sign in" / "Get started" links. Also render a `.flash-banner` when a `signed_out` flag is present so `/` can confirm the sign-out.
  - `templates/landing.html` — no structural change; it inherits the new navbar automatically. Only touch it if the signed-out message needs a placement block.

## Files to change
- `app.py` — import `os`, `session`, `check_password_hash`, `functools.wraps`; set `app.secret_key`; add `login_required` and `current_user_id` helpers; implement `POST /login`, `POST /logout`; guard `/profile`
- `templates/login.html` — form action, email re-population, hidden `next` field
- `templates/base.html` — session-aware navbar, sign-out form, signed-out banner
- `static/css/style.css` — add rules for the logged-in navbar (`.nav-user`, `.nav-logout`) and `.flash-banner`, using existing variables only

## Files to create
None.

## New dependencies
No new dependencies. `flask.session`, `werkzeug.security.check_password_hash` and `functools` are all already available (`flask==3.1.3`, `werkzeug==3.1.6`).

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never string-format SQL
- Passwords hashed with werkzeug; verify with `check_password_hash(row["password_hash"], password)` and never store, log or re-render a plaintext password
- Use CSS variables — never hardcode hex values (add new variables to `:root` if a colour is missing)
- All templates extend `base.html`
- Use `get_db()` from `database/db.py`; open the connection inside the request and close it in a `try/finally`
- Secret key: `app.secret_key = os.environ.get("SECRET_KEY", "dev-only-insecure-key")`. Never commit a real secret and never hardcode a production value in `app.py`
- Normalise the submitted email with `.strip().lower()` before the lookup, matching how Step 2 stores it. Do not strip the password
- Use a single generic error — "Invalid email or password." — for both an unknown email and a wrong password, so the form cannot be used to discover which addresses are registered. Re-render with HTTP 200 and the email preserved
- On success store only `session["user_id"]` and `session["user_name"]` — never the email or the hash. Call `session.clear()` before populating it so a stale session cannot leak across logins
- Redirect after login to the `next` form value when it is a safe relative path (starts with `/`, does not start with `//`, and contains no `\`); otherwise `url_for("profile")`. Reject absolute URLs to avoid an open redirect
- `logout()` calls `session.clear()` then `redirect(url_for("landing", signed_out=1))`; it must work even when no one is logged in
- `login_required` is a `functools.wraps` decorator that redirects to `url_for("login", next=request.path)` when `session.get("user_id")` is missing. Apply it to `/profile` only in this step
- `GET /login` for a user who already has `session["user_id"]` redirects to `url_for("profile")` instead of rendering the form
- Keep the `registered=1` success banner from Step 2 working
- Do not build the profile page, dashboard or expense routes; `/profile` keeps returning its placeholder string, just gated

## Definition of done
- [ ] App starts with `python app.py` without errors; `/`, `/login`, `/register`, `/terms`, `/privacy` all return 200
- [ ] `POST /login` with `demo@spendly.com` / `demo123` returns a 302 to `/profile` and sets a session cookie
- [ ] After that login, `/profile` returns 200 with the placeholder text, and the navbar shows "Demo User" and a "Sign out" button instead of "Sign in / Get started"
- [ ] `POST /login` with a correct email and wrong password re-renders the form with "Invalid email or password." and the email still filled in
- [ ] `POST /login` with an unregistered email shows the same "Invalid email or password." message — the two cases are indistinguishable
- [ ] `POST /login` with `Demo@Spendly.com` succeeds (email match is case-insensitive)
- [ ] The submitted password never appears in the re-rendered HTML after a failed login
- [ ] Visiting `/profile` while logged out redirects (302) to `/login?next=/profile`; logging in from that page lands on `/profile`
- [ ] A `next` value of `https://example.com` or `//example.com` is ignored and login lands on `/profile`
- [ ] `POST /logout` returns 302 to `/`, the landing page shows a signed-out message, and `/profile` redirects to `/login` again afterwards
- [ ] `GET /logout` returns 405 (POST-only), and `POST /logout` while already logged out still redirects to `/` without an error
- [ ] `GET /login` while logged in redirects (302) to `/profile`
- [ ] `/login?registered=1` still shows the green "Account created. Please sign in." box
- [ ] Registering a new account at `/register` and then signing in with it works end to end
- [ ] `grep -n "#[0-9a-fA-F]\{3,6\}" static/css/style.css` shows colours only inside `:root`
