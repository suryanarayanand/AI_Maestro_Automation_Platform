from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from web.routes.auth import login_required
from web.services.app_memory_service import capture_current_screen, memory_summary, rebuild_memory
from web.services.source_locator_service import import_source_locators
from web.portal_db import connect


app_memory_bp = Blueprint("app_memory", __name__)


@app_memory_bp.route("/app-memory")
@login_required
def index():
    totals, screens, learning = memory_summary()
    return render_template("app_memory.html", totals=totals, screens=screens, learning=learning)


@app_memory_bp.route("/app-memory/rebuild", methods=["POST"])
@login_required
def rebuild():
    try:
        result = rebuild_memory()
        flash(
            f"App Memory rebuilt from {result['hierarchies']} hierarchies and "
            f"{result['validated_locators']} validated locator records.",
            "success",
        )
    except Exception as exc:
        flash(f"App Memory rebuild failed: {exc}", "danger")
    return redirect(url_for("app_memory.index"))


@app_memory_bp.route("/app-memory/capture", methods=["POST"])
@login_required
def capture():
    try:
        result = capture_current_screen(request.form.get("screen_name", "current_screen"))
        flash(
            f"Learned {result['screen']} with {result['elements']} selector candidates. No controls were tapped.",
            "success",
        )
    except Exception as exc:
        flash(f"Current-screen capture failed: {exc}", "danger")
    return redirect(url_for("app_memory.index"))


@app_memory_bp.route("/app-memory/import-source", methods=["POST"])
@login_required
def import_source():
    source_root = request.form.get("source_root", "").strip()
    try:
        result = import_source_locators(source_root)
    except (OSError, ValueError) as exc:
        flash(f"Source locator import failed: {exc}", "danger")
    else:
        flash(
            f"Imported {result['count']} source locator candidates "
            f"({result['strong']} strong). Validate them on an installed build before use.",
            "success",
        )
    return redirect(url_for("app_memory.index"))


@app_memory_bp.route("/app-memory/learning/<int:learning_id>/<decision>", methods=["POST"])
@login_required
def review_learning(learning_id, decision):
    if decision not in {"accepted", "rejected"}:
        flash("Invalid learning decision.", "danger")
        return redirect(url_for("app_memory.index"))
    with connect() as db:
        db.execute(
            """UPDATE app_memory_learning SET status=?,reviewed_at=CURRENT_TIMESTAMP,reviewed_by=?
               WHERE id=? AND status='pending'""",
            (decision, session["username"], learning_id),
        )
    flash(f"Learning proposal {decision}. Acceptance records approval; it does not silently create a locator.", "success")
    return redirect(url_for("app_memory.index"))
