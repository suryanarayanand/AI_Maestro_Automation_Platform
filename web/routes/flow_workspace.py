from pathlib import Path

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from web.services.atomic_flow_service import (
    generate_proposal,
    get_step,
    import_catalog,
    list_steps,
    create_manual_step,
    proposal_readiness,
    proposal_guidance,
    publish_proposal,
    save_proposal,
    update_step_context,
)


ROOT = Path(__file__).resolve().parents[2]
flow_workspace_bp = Blueprint("flow_workspace", __name__)


@flow_workspace_bp.route("/flow-workspace/new", methods=["GET", "POST"])
def new_intake():
    if request.method == "POST":
        try:
            step_id = create_manual_step(
                request.form.get("scenario"), request.form.get("action"),
                request.form.get("user_state"), request.form.get("module"),
                request.form.get("tags"),
            )
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Manual intake created. Verify context before generating.", "success")
            return redirect(url_for("flow_workspace.review", step_id=step_id))
    return render_template("flow_workspace_new.html")


@flow_workspace_bp.route("/flow-workspace", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        upload = request.files.get("excel")
        if not upload or not upload.filename.lower().endswith(".xlsx"):
            flash("Select a valid catalogue .xlsx workbook.", "danger")
        else:
            path = ROOT / "Uploads" / secure_filename(upload.filename)
            upload.save(path)
            try:
                count = import_catalog(path)
            except ValueError as exc:
                flash(str(exc), "danger")
            else:
                flash(f"Imported {count} new atomic flow steps. YAML is generated on demand.", "success")
        return redirect(url_for("generator.generator") + "#atomic-flows")
    query = request.query_string.decode("utf-8")
    destination = url_for("generator.generator") + (f"?{query}" if query else "")
    return redirect(destination + "#atomic-flows")


@flow_workspace_bp.route("/flow-workspace/<int:step_id>", methods=["GET", "POST"])
def review(step_id):
    step = get_step(step_id)
    if not step:
        abort(404)
    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "context":
                update_step_context(
                    step_id, request.form.get("user_state", ""), request.form.get("tags", "")
                )
                flash("Generation context updated.", "success")
            elif action == "generate":
                generate_proposal(step_id)
                flash("Proposal generation completed.", "success")
            elif action == "save":
                save_proposal(step_id, request.form.get("yaml", ""))
                flash("Proposal edits saved.", "success")
            elif action == "publish":
                path = publish_proposal(
                    step_id, request.form.get("yaml", ""), session.get("username", "")
                )
                flash(f"Flow approved and published to {path}.", "success")
            else:
                raise ValueError("Unknown review action.")
        except Exception as exc:
            flash(str(exc), "danger")
        return redirect(url_for("flow_workspace.review", step_id=step_id))
    return render_template(
        "flow_workspace_review.html", step=step,
        readiness=proposal_readiness(step) if step.get("proposal_yaml") else None,
        guidance=proposal_guidance(step),
    )
