import sqlite3
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash, abort, session
from werkzeug.security import check_password_hash

from database.db import get_db, init_db, seed_db, create_user, get_user_by_email, get_user_by_id
from database.queries import (
    get_user_by_id as get_profile_user,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

with app.app_context():
    init_db()
    seed_db()


@app.context_processor
def inject_current_user():
    if session.get("user_id"):
        return {"current_user": get_user_by_id(session["user_id"])}
    return {"current_user": None}


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    user = None
    if session.get("user_id"):
        user = get_user_by_id(session["user_id"])
    return render_template("landing.html", user=user)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not name or not email or not password or not confirm_password:
        return render_template("register.html", error="All fields are required.")

    if password != confirm_password:
        return render_template("register.html", error="Passwords do not match.")

    if len(password) < 8:
        return render_template(
            "register.html", error="Password must be at least 8 characters."
        )

    if get_user_by_email(email) is not None:
        return render_template("register.html", error="Email already registered.")

    try:
        create_user(name, email, password)
    except sqlite3.IntegrityError:
        return render_template("register.html", error="Email already registered.")

    flash("Account created! Please sign in.")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("landing"))
        return render_template("login.html")

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    user = get_user_by_email(email)

    if user and check_password_hash(user["password_hash"], password):
        session.clear()
        session["user_id"] = user["id"]
        return redirect(url_for("landing"))

    return render_template("login.html", error="Invalid email or password")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


def _parse_date_param(value):
    if not value:
        return None
    try:
        # Only used to validate the format; the original string is returned
        # since expenses.date is stored as ISO text, not a datetime object.
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None
    return value


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    start_date = _parse_date_param(request.args.get("start_date"))
    end_date = _parse_date_param(request.args.get("end_date"))
    if start_date and end_date and end_date < start_date:
        end_date = None

    user = get_profile_user(session["user_id"])
    stats = get_summary_stats(session["user_id"], start_date=start_date, end_date=end_date)
    transactions = get_recent_transactions(session["user_id"], start_date=start_date, end_date=end_date)
    categories = get_category_breakdown(session["user_id"], start_date=start_date, end_date=end_date)

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
        start_date=start_date,
        end_date=end_date,
    )


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
