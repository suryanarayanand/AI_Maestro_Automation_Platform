from functools import wraps
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash
from web.portal_db import connect

auth_bp = Blueprint("auth", __name__)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("username"):
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        with connect() as db:
            user = db.execute("SELECT * FROM users WHERE username=?", (request.form["username"],)).fetchone()
        if user and check_password_hash(user["password_hash"], request.form["password"]):
            session["username"], session["role"] = user["username"], user["role"]
            return redirect(request.args.get("next") or url_for("dashboard.dashboard"))
        flash("Invalid username or password", "danger")
    return render_template("login.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
