import json
from pathlib import Path
from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename
from web.portal_db import connect
from web.routes.auth import login_required
from web.services.generation_service import approve_draft, create_drafts, reject_draft

ROOT = Path(__file__).resolve().parents[2]
generator_bp = Blueprint("generator", __name__)


@generator_bp.route("/generator", methods=["GET", "POST"])
@login_required
def generator():
    if request.method == "POST":
        upload = request.files.get("excel")
        if not upload or not upload.filename.lower().endswith(".xlsx"):
            flash("Select a valid .xlsx workbook", "danger")
        else:
            path = ROOT / "Uploads" / secure_filename(upload.filename)
            upload.save(path)
            try:
                use_ai = request.form.get("use_ai") == "1"
                ids, normalization = create_drafts(path, use_ai=use_ai)
                flash(
                    f"Converted {normalization.sheet_count} worksheet(s) to the supported "
                    f"Excel format: {normalization.case_count} cases and "
                    f"{normalization.step_count} steps. "
                    f"Created {len(ids)} YAML draft(s) for review"
                    f"{' with automatic AI fallback' if use_ai else ''}.",
                    "success",
                )
            except Exception as exc:
                flash(str(exc), "danger")
        return redirect(url_for("generator.generator"))
    with connect() as db:
        drafts = db.execute("SELECT * FROM drafts ORDER BY id DESC").fetchall()
    return render_template("generator.html", drafts=drafts)


@generator_bp.route("/generator/<int:draft_id>")
@login_required
def review(draft_id):
    with connect() as db:
        draft = db.execute("SELECT * FROM drafts WHERE id=?", (draft_id,)).fetchone()
    if not draft:
        abort(404)
    assumptions = json.loads(draft["ai_assumptions"] or "[]")
    return render_template("review_yaml.html", draft=draft, assumptions=assumptions)


@generator_bp.route("/generator/<int:draft_id>/approve", methods=["POST"])
@login_required
def approve(draft_id):
    try:
        approve_draft(draft_id, request.form["yaml"], request.form["suite"], session["username"])
        flash("YAML approved and added to the suite", "success")
    except Exception as exc:
        flash(str(exc), "danger")
    return redirect(url_for("generator.generator"))


@generator_bp.route("/generator/<int:draft_id>/reject", methods=["POST"])
@login_required
def reject(draft_id):
    reject_draft(draft_id, session["username"])
    flash("Draft rejected", "warning")
    return redirect(url_for("generator.generator"))
