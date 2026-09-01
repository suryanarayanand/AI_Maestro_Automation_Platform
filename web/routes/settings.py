import subprocess

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from web.portal_db import connect
from web.services.repository_metadata_service import (
    application_repository_status,
    save_application_repository_configuration,
    sync_application_repository,
)

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/settings/help")
def help_guide():
    return render_template("help_guide.html")


@settings_bp.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        action = request.form.get("action", "execution")
        if action == "theme":
            theme = request.form.get("portal_theme", "light").strip().lower()
            if theme not in {"light", "dark"}:
                flash("Choose Light or Dark theme.", "danger")
            else:
                key = f"portal_theme:{session['username']}"
                with connect() as db:
                    db.execute(
                        "INSERT INTO portal_settings(key,value,updated_at) VALUES(?,?,CURRENT_TIMESTAMP) "
                        "ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=CURRENT_TIMESTAMP",
                        (key, theme),
                    )
                flash(f"{theme.title()} theme applied.", "success")
            return redirect(url_for("settings.settings"))
        if action == "repository":
            try:
                save_application_repository_configuration(
                    request.form.get("repository_url", ""),
                    request.form.get("repository_path", ""),
                    request.form.get("repository_token", ""),
                )
            except ValueError as exc:
                flash(str(exc), "danger")
            else:
                flash("Application repository settings saved in the local .env. The token remains masked.", "success")
            return redirect(url_for("settings.settings"))
        if action == "pull":
            try:
                result = sync_application_repository()
            except (ValueError, subprocess.TimeoutExpired) as exc:
                flash(f"Application repository sync failed: {exc}", "danger")
            else:
                flash(f"Application repository sync completed: {result}", "success")
            return redirect(url_for("settings.settings"))
        if action == "application_pull":
            try:
                result = sync_application_repository()
            except (ValueError, subprocess.TimeoutExpired) as exc:
                flash(f"Application repository sync failed: {exc}", "danger")
            else:
                flash(f"Application repository sync completed: {result}", "success")
            return redirect(url_for("settings.settings"))
        try:
            timeout = int(request.form.get("case_timeout_seconds", ""))
            if not 30 <= timeout <= 3600:
                raise ValueError
            batch_size = int(request.form.get("execution_batch_size", "10"))
            if not 1 <= batch_size <= 100:
                raise ValueError
        except ValueError:
            flash("Case timeout must be between 30 and 3600 seconds; batch size must be 1-100.", "danger")
        else:
            with connect() as db:
                for key, value in (("case_timeout_seconds", timeout),
                                   ("execution_batch_size", batch_size)):
                    db.execute(
                        "INSERT INTO portal_settings(key,value,updated_at) VALUES(?,?,CURRENT_TIMESTAMP) "
                        "ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=CURRENT_TIMESTAMP",
                        (key, str(value)),
                    )
            flash("Execution settings saved. They apply to newly claimed jobs.", "success")
            return redirect(url_for("settings.settings"))
    repository = application_repository_status()
    with connect() as db:
        values = {row["key"]: row["value"] for row in db.execute(
            "SELECT key,value FROM portal_settings"
        )}
    return render_template(
        "settings.html", case_timeout_seconds=int(values.get("case_timeout_seconds", 300)),
        execution_batch_size=int(values.get("execution_batch_size", 10)), repository=repository,
        repository_token_saved=repository["token_configured"],
        portal_theme=values.get(f"portal_theme:{session['username']}", "light"),
    )
