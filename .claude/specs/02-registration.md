# Spec: Registration

## Overview
Turn the existing static `/register` page into a working sign-up flow. A visitor submits their name, email and password; the server validates the input, rejects duplicate emails, hashes the password with werkzeug, inserts a row into the `users` table created in Step 1, and redirects to `/login` with a success message. This is the first feature that writes user-supplied data to the database and it is the entry point for every logged-in feature that follows (login/logout, profile, expenses).

## Depends on
- Step 1 — Database Setup (`users` table, `get_db()` in `database/db.py`)

## Routes
- `GET /register` — render the registration form (already exists; keep behaviour) — public
- `POST /register` — validate the form, create the user, redirect to `/login` on success; re-render the form with an error on failure — public

Change the existing `@app.route("/register")` to `methods=["GET", "POST"]`. No other routes change; `/login` remains a GET-only placeholder until Step 3.

## Database changes
No database changes. The `users` table (`id`, `name`, `email UNIQUE NOT NULL`, `password_hash NOT NULL`, `created_at DEFAULT datetime('now')`) already supports everything required. Rely on the existing UNIQUE constraint as the last line of defence against duplicate emails, but check for duplicates explicitly first so the user gets a friendly message instead of a 500.

## Templates
- **Create:** none
- **Modify:**
  - `templates/register.html` — keep the form; re-populate `name` and `email` from the previous submission on error (`value="{{ name or '' }}"`), never re-populate the password. Add `minlength="8"` to the password input to match the placeholder. The existing `{% if error %}` block already renders `.auth-error`.
  - `templates/login.html` — render a `.auth-success` box when a `success` variable is passed (used for "Account created. Please sign in."). `/login` stays a stub route until Step 3, so pass the message via a query flag (`/login?registered=1`) and read `request.args` in the existing `login()` view.

## Files to change
- `app.py` — import `request`, `redirect`, `url_for`; implement `POST /register`; read `registered` flag in `login()`
- `templates/register.html` — re-populate fields, `minlength`
- `templates/login.html` — success banner
- `static/css/style.css` — add `--success` / `--success-light` variables to `:root` and an `.auth-success` rule mirroring `.auth-error`

## Files to create
None.

## New dependencies
No new dependencies. Use `werkzeug.security.generate_password_hash` (already installed) and `sqlite3`.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never string-format SQL
- Passwords hashed with werkzeug `generate_password_hash`; never store or log plaintext
- Use CSS variables — never hardcode hex values (add new variables to `:root` if a colour is missing)
- All templates extend `base.html`
- Use `get_db()` from `database/db.py`; open the connection inside the request and close it in a `try/finally`
- Validation rules (server-side, in this order; return the first failure):
  1. All three fields present after `.strip()` (password is not stripped)
  2. `name` between 2 and 80 characters
  3. `email` looks like an email (contains `@` and a `.` after it) and is at most 254 characters; normalise to lowercase before checking and storing
  4. `password` at least 8 characters
  5. Email not already in `users` (`SELECT id FROM users WHERE email = ?`)
- On validation failure: `render_template("register.html", error=..., name=..., email=...)` with HTTP 200 (matches existing template contract); never echo the password
- On success: `INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)`, `commit()`, then `redirect(url_for("login", registered=1))`
- Wrap the INSERT in `try/except sqlite3.IntegrityError` and show "An account with that email already exists." if the race with the UNIQUE constraint is lost
- Do not log the user in yet — sessions are Step 3
- Do not touch `/logout`, `/profile` or expense routes

## Definition of done
- [ ] `GET /register` still renders the form with a 200
- [ ] Submitting valid data creates a row in `users` with a werkzeug hash (verify with `check_password_hash`) and redirects (302) to `/login?registered=1`
- [ ] `/login?registered=1` shows a green "Account created" success box; plain `/login` does not
- [ ] Submitting with any field blank re-renders the form with an error and the name/email preserved
- [ ] Password shorter than 8 characters is rejected with an error
- [ ] Malformed email (e.g. `notanemail`) is rejected with an error
- [ ] Registering `demo@spendly.com` (already seeded) shows "An account with that email already exists." and does not create a row
- [ ] Registering `Demo@Spendly.com` is treated as the same email (case-insensitive)
- [ ] Password value is never present in the re-rendered HTML after an error
- [ ] `grep -n "#[0-9a-fA-F]\{3,6\}" static/css/style.css` shows new colours only inside `:root`
- [ ] App starts with `python app.py` without errors and `/`, `/login`, `/terms`, `/privacy` still return 200
