from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from web.routes.auth import login_required
from web.services.yaml_editor_service import delete_scenario, list_scenarios, read_scenario, save_scenario

yaml_editor_bp = Blueprint("yaml_editor", __name__)


@yaml_editor_bp.route("/yaml-editor")
@login_required
def index():
    query = request.args.get("q", "")
    return render_template("yaml_editor.html", scenarios=list_scenarios(query), query=query)


def render_editor(scenario_path):
    try:
        if request.method == "POST":
            backup = save_scenario(scenario_path, request.form.get("yaml", ""))
            flash(f"YAML saved. Backup: {backup}", "success")
            return redirect(url_for("yaml_editor.edit_query", file=scenario_path))
        content = read_scenario(scenario_path)
    except FileNotFoundError:
        abort(404)
    except ValueError as exc:
        if request.method == "POST":
            flash(str(exc), "danger")
            content = request.form.get("yaml", "")
        else:
            abort(400)
    return render_template("yaml_editor_edit.html", scenario_path=scenario_path, yaml_content=content)


@yaml_editor_bp.route("/yaml-editor/edit", methods=["GET", "POST"])
@login_required
def edit_query():
    scenario_path = request.args.get("file", "")
    if not scenario_path:
        abort(400)
    return render_editor(scenario_path)


@yaml_editor_bp.route("/yaml-editor/<path:scenario_path>", methods=["GET", "POST"])
@login_required
def edit(scenario_path):
    return render_editor(scenario_path)


@yaml_editor_bp.route("/yaml-editor/delete", methods=["POST"])
@login_required
def delete():
    scenario_path = request.form.get("file", "")
    if not scenario_path:
        abort(400)
    try:
        backup = delete_scenario(scenario_path)
    except FileNotFoundError:
        abort(404)
    except ValueError as exc:
        flash(str(exc), "danger")
    else:
        flash(f"YAML deleted. Recovery backup: {backup}", "success")
    return redirect(url_for("yaml_editor.index"))
