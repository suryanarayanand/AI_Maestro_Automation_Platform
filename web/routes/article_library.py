from pathlib import Path

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from web.services.article_reference_service import (
    archive_reference, get_reference, import_reference_workbook, list_references, save_reference,
)

ROOT = Path(__file__).resolve().parents[2]
article_library_bp = Blueprint("article_library", __name__)


@article_library_bp.route("/article-library", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        action = request.form.get("action", "save")
        try:
            if action == "import":
                upload = request.files.get("excel")
                if not upload or not upload.filename.lower().endswith(".xlsx"):
                    raise ValueError("Select a valid .xlsx reference workbook.")
                path = ROOT / "Uploads" / secure_filename(upload.filename)
                upload.save(path)
                count = import_reference_workbook(path)
                flash(f"Imported {count} new article references.", "success")
            else:
                save_reference(
                    request.form.get("reference_id"), request.form.get("label"),
                    request.form.get("url"), request.form.get("article_type"),
                    request.form.get("user_state"), request.form.get("notes"),
                )
                flash("Article reference saved.", "success")
        except Exception as exc:
            flash(str(exc), "danger")
        return redirect(url_for("article_library.index"))
    references, types = list_references(
        request.args.get("q", ""), request.args.get("type", ""), request.args.get("state", "")
    )
    return render_template(
        "article_library.html", references=references, types=types,
        query=request.args.get("q", ""), selected_type=request.args.get("type", ""),
        selected_state=request.args.get("state", ""),
    )


@article_library_bp.route("/article-library/<int:reference_id>/edit")
def edit(reference_id):
    reference = get_reference(reference_id)
    if not reference:
        abort(404)
    references, types = list_references()
    return render_template("article_library.html", references=references, types=types,
                           editing=reference, query="", selected_type="", selected_state="")


@article_library_bp.route("/article-library/<int:reference_id>/archive", methods=["POST"])
def archive(reference_id):
    if not get_reference(reference_id):
        abort(404)
    archive_reference(reference_id)
    flash("Article reference archived. Historical test evidence is unchanged.", "success")
    return redirect(url_for("article_library.index"))
