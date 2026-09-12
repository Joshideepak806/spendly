import os
import sqlite3
from datetime import date
from functools import wraps

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import get_db, init_db, seed_db
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)

app = Flask(__name__)

# Signs the session cookie. Set SECRET_KEY in the environment for anything
# that is not local development; never commit a real secret.
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-insecure-key")

# Make sure the schema exists and demo data is present before serving.
with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def validate_registration(name, email, password):
    """Return an error message for invalid input, or None if it is valid.

    `name` and `email` are expected to be stripped already; `password`
    is checked as-is and never modified.
    """
    if not name or not email or not password:
        return "All fields are required."
    if not (2 <= len(name) <= 80):
        return "Name must be between 2 and 80 characters."
    at = email.find("@")
    if len(email) > 254 or at < 1 or "." not in email[at + 1:]:
        return "Please enter a valid email address."
    if len(password) < 8:
        return "Password must be at least 8 characters."
    return None


def safe_next(target):
    """Return `target` if it is a relative path we are willing to redirect to.

    Anything absolute (`https://evil.example`, `//evil.example`) or containing a
    backslash is discarded, so `?next=` cannot be used as an open redirect.
    """
    if not target or not target.startswith("/") or target.startswith("//"):
        return None
    if "\\" in target:
        return None
    return target


def initials(name):
    """Return up to two upper-case initials for an avatar, or "?" for a blank name."""
    words = name.split()
    if not words:
        return "?"
    letters = words[0][0] + (words[-1][0] if len(words) > 1 else "")
    return letters.upper()


def login_required(view):
    """Redirect anonymous visitors to the sign-in page, remembering where they were."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    error = validate_registration(name, email, password)
    if error:
        return render_template("register.html", error=error, name=name, email=email)

    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()
        if existing:
            return render_template(
                "register.html",
                error="An account with that email already exists.",
                name=name,
                email=email,
            )
        try:
            conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name, email, generate_password_hash(password)),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            # Lost the race against a concurrent registration for the same email.
            return render_template(
                "register.html",
                error="An account with that email already exists.",
                name=name,
                email=email,
            )
    finally:
        conn.close()

    return redirect(url_for("login", registered=1))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("profile"))
        success = None
        if request.args.get("registered") == "1":
            success = "Account created. Please sign in."
        return render_template(
            "login.html", success=success, next=request.args.get("next")
        )

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    target = request.form.get("next")

    # One message for a blank field, an unknown email and a wrong password
    # alike, so the form cannot be used to discover which emails are registered.
    invalid = "Invalid email or password."

    conn = get_db()
    try:
        user = conn.execute(
            "SELECT id, name, password_hash FROM users WHERE email = ?", (email,)
        ).fetchone()
    finally:
        conn.close()

    if not user or not check_password_hash(user["password_hash"], password):
        return render_template(
            "login.html", error=invalid, email=email, next=target
        )

    # Start from a clean session so nothing leaks across logins.
    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]

    return redirect(safe_next(target) or url_for("profile"))


@app.route("/logout", methods=["POST"])
def logout():
    # POST only: a GET /logout could be fired by any third-party page embedding
    # it as an image or link, silently signing the user out.
    session.clear()
    return redirect(url_for("landing", signed_out=1))


@app.route("/profile")
@login_required
def profile():
    user_id = session["user_id"]

    user = get_user_by_id(user_id)
    if not user:
        # The account was deleted while its session cookie was still valid.
        session.clear()
        return redirect(url_for("login"))

    stats = get_summary_stats(user_id)

    return render_template(
        "profile.html",
        user=user,
        initials=initials(user["name"]),
        member_since=user["member_since"],
        total_spent=stats["total_spent"],
        month_spent=stats["month_spent"],
        expense_count=stats["transaction_count"],
        top_category=stats["top_category"],
        month_name=date.today().strftime("%B"),
        transactions=get_recent_transactions(user_id),
        categories=get_category_breakdown(user_id),
    )


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
