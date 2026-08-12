from flask import Blueprint, flash, redirect, render_template, request, url_for

from web.portal_db import connect

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        try:
            timeout = int(request.form.get("case_timeout_seconds", ""))
            if not 30 <= timeout <= 3600:
                raise ValueError
        except ValueError:
            flash("Case timeout must be between 30 and 3600 seconds.", "danger")
        else:
            with connect() as db:
                db.execute(
                    "INSERT INTO portal_settings(key,value,updated_at) VALUES(?,?,CURRENT_TIMESTAMP) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=CURRENT_TIMESTAMP",
                    ("case_timeout_seconds", str(timeout)),
                )
            flash("Execution settings saved. They apply to newly claimed jobs.", "success")
            return redirect(url_for("settings.settings"))
    with connect() as db:
        row = db.execute(
            "SELECT value FROM portal_settings WHERE key='case_timeout_seconds'"
        ).fetchone()
    return render_template("settings.html", case_timeout_seconds=int(row["value"]) if row else 300)
