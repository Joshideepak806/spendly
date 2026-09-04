# Spec: Profile Page

## Overview
Replace the `/profile` placeholder string with a real, designed profile page — the first screen a user lands on after signing in. It shows who they are (name, email, member-since date, an initials avatar) and a compact snapshot of their spending pulled from the `expenses` table: total spent, spent this month, number of expenses logged, and their top category. This step is design-first: it introduces the logged-in page layout (`.page` shell, stat tiles, cards) that the dashboard and expense screens in later steps will reuse, and it is the first feature to read a user's expenses from the database. Editing the profile, listing expenses and the full dashboard are out of scope and belong to later steps.

## Depends on
- Step 1 — Database Setup (`users` and `expenses` tables, `get_db()` in `database/db.py`)
- Step 2 — Registration (users have `name`, `email`, `created_at`)
- Step 3 — Login and Logout (`session["user_id"]`, `login_required`, session-aware navbar)

## Routes
- `GET /profile` — render the profile page for the current user, with account details and spending summary — logged-in

The route already exists with `@login_required`; only its body changes. No new routes. `POST /profile` (editing name or password) is deliberately not part of this step.

## Database changes
No database changes. Everything needed is already in the schema:
- `users.name`, `users.email`, `users.created_at` for the account card
- `expenses.amount`, `expenses.category`, `expenses.date`, `expenses.user_id` for the summary

The summary is read-only aggregate SQL, always filtered by `user_id = ?`:
- Total spent and count: `SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count FROM expenses WHERE user_id = ?`
- This month: same query with `AND date >= ?` where the parameter is the first day of the current month as `YYYY-MM-DD`
- Top category: `SELECT category, SUM(amount) AS total FROM expenses WHERE user_id = ? GROUP BY category ORDER BY total DESC LIMIT 1`

## Templates
- **Create:**
  - `templates/profile.html` — extends `base.html`; a `.page` wrapper containing a `.page-header` (eyebrow "Your account", title "Hi, {name}"), a `.profile-card` (initials avatar, name, email, "Member since {Month YYYY}"), a `.stat-grid` of four `.stat-tile`s (Total spent, This month, Expenses logged, Top category), and a `.profile-actions` row with a "Add expense" link to `url_for('add_expense')`. Show an `.empty-state` message inside the stats area when the user has no expenses yet
- **Modify:**
  - `templates/base.html` — no structural change required; the navbar already links the user's name to `/profile`. Only touch it if a `{% block %}` is missing

## Files to change
- `app.py` — implement `profile()`: look up the user by `session["user_id"]`, run the three aggregate queries, compute the initials and month-start date, and `render_template("profile.html", ...)`. If the session's `user_id` no longer exists in `users`, clear the session and redirect to `/login`
- `static/css/style.css` — add a "Logged-in pages" section with rules for `.page`, `.page-header`, `.page-eyebrow`, `.page-title`, `.profile-card`, `.avatar`, `.profile-meta`, `.stat-grid`, `.stat-tile`, `.stat-label`, `.stat-value`, `.stat-hint`, `.profile-actions`, `.empty-state`, plus responsive rules at the existing 900px and 600px breakpoints. Reuse existing variables (`--paper-card`, `--border`, `--accent`, `--font-display`, `--radius-md`); add new variables to `:root` only if a colour is genuinely missing

## Files to create
- `templates/profile.html`

## New dependencies
No new dependencies. Use `sqlite3`, `datetime.date` (standard library) and Flask's `render_template` / `session`, all already available.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never string-format SQL
- Passwords hashed with werkzeug (no password handling in this step; never select or render `password_hash`)
- Use CSS variables — never hardcode hex values (add new variables to `:root` if a colour is missing)
- All templates extend `base.html`
- Use `get_db()` from `database/db.py`; open the connection inside the request and close it in a `try/finally`
- Every expenses query must filter by `user_id = ?` using `session["user_id"]` — never trust an id from the query string or form
- Select only the columns the page needs: `SELECT id, name, email, created_at FROM users WHERE id = ?`
- Compute the month-start date in Python (`date.today().replace(day=1).isoformat()`) and pass it as a parameter; do not use SQLite `strftime` on user data
- Format currency in the template as `₹{{ "%.2f"|format(value) }}` (or `"{:,.2f}"`), matching the rupee branding used on the landing page; amounts are `REAL`, so always coerce `None` from `SUM` to `0` with `COALESCE`
- Initials: first letter of the first word and first letter of the last word of `name`, upper-cased, max two characters; handle single-word names
- "Member since" is derived from `users.created_at` (format `YYYY-MM-DD HH:MM:SS`); parse the first 10 characters and render as `Month YYYY`
- Keep `login_required` on the route; if `SELECT ... FROM users WHERE id = ?` returns no row (user deleted while their cookie is still valid), `session.clear()` and `redirect(url_for("login"))`
- The "Add expense" link points at the existing `/expenses/add` placeholder; do not implement expense routes in this step
- Do not add profile editing, a password change form, an expense list, charts or filters — those are later steps
- Match existing template conventions: `{% block title %}Profile — Spendly{% endblock %}`, semantic `<section>`/`<h1>`, no inline `style=` attributes
- Keep `templates/profile.html` free of JavaScript; `static/js/main.js` stays unchanged

## Definition of done
- [ ] App starts with `python app.py` without errors; `/`, `/login`, `/register`, `/terms`, `/privacy` still return 200
- [ ] Visiting `/profile` while logged out still redirects (302) to `/login?next=/profile`
- [ ] After signing in as `demo@spendly.com` / `demo123`, `/profile` returns 200 and renders `profile.html` (no more "coming in Step 4" text anywhere in the app for this route)
- [ ] The page shows "Demo User", `demo@spendly.com`, an avatar with "DU", and a "Member since" line with a month and year
- [ ] Stat tiles show Total spent `₹395.59`, This month `₹395.59` (seed data is dated in the current month), Expenses logged `8`, and Top category `Bills`
- [ ] Register a brand-new account, sign in, visit `/profile`: totals show `₹0.00`, count shows `0`, top category shows a dash or "—", and the empty-state message is visible
- [ ] A user with a single-word name (e.g. "Cher") shows a one-letter avatar without an error
- [ ] The page never contains the string `password_hash` or any hash value in its HTML
- [ ] The navbar shows the user's name and "Sign out"; clicking "Sign out" then reloading `/profile` redirects to `/login`
- [ ] The "Add expense" link resolves to `/expenses/add` and returns its Step 7 placeholder
- [ ] Manually deleting the demo user row from `spendly.db` while its session cookie is still set causes `/profile` to redirect to `/login` rather than raise a 500
- [ ] At 600px wide the stat grid collapses to a single column and nothing overflows horizontally
- [ ] `grep -n "#[0-9a-fA-F]\{3,6\}" static/css/style.css` shows colours only inside `:root` (plus the pre-existing `.mock-*` landing-page rules)
- [ ] `grep -n "user_id" app.py` shows every expenses query filtered by the session's `user_id`
