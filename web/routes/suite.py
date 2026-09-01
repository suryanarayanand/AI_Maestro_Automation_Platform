import json
import re
from pathlib import Path
from flask import Blueprint, render_template, redirect, url_for, flash, request

from web.services.scenario_service import (delete_suite, get_all_suites, get_suite_editor,
                                           save_suite_tests, validate_suite_definition)
from web.portal_db import connect
from web.services.job_queue_service import create_batched_jobs

suite_bp = Blueprint("suite", __name__)
ROOT = Path(__file__).resolve().parents[2]


@suite_bp.route("/suites")
def suites():
    order = {
        "user_anonymous": (0, "Anonymous User", "A", "anonymous"),
        "user_subscriber": (1, "Subscriber", "S", "subscriber"),
        "user_registered": (2, "Registered User", "R", "registered"),
        "user_expired": (3, "Expired User", "E", "expired"),
        "smoke": (4, "Smoke", "SM", "smoke"),
        "regression": (5, "Regression", "RG", "regression"),
        "visual_regression": (6, "Visual Regression", "VR", "visual"),
    }
    suites_by_key = {suite["key"]: suite for suite in get_all_suites()}
    visible_suites = []
    for key, (position, label, icon, tone) in order.items():
        suite = suites_by_key.get(key)
        if not suite:
            continue
        suite = dict(suite)
        suite.update(label=label, icon=icon, tone=tone, position=position)
        visible_suites.append(suite)
    return render_template("scenarios.html", suites=visible_suites)


@suite_bp.route("/suites/<suite_name>/edit", methods=["GET", "POST"])
def edit_suite(suite_name):
    editor = get_suite_editor(suite_name)
    if editor is None:
        flash("Suite not found.", "danger")
        return redirect(url_for("suite.suites"))
    if request.method == "POST":
        try:
            count = save_suite_tests(
                editor["key"], request.form.getlist("tests"), request.form.getlist("modules")
            )
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash(f"{editor['name']} saved with {count} test cases.", "success")
            return redirect(url_for("suite.edit_suite", suite_name=editor["key"]))
        editor = get_suite_editor(editor["key"])
    return render_template("suite_editor.html", suite=editor)


@suite_bp.route("/suites/<suite_name>/delete", methods=["POST"])
def remove_suite(suite_name):
    editor = get_suite_editor(suite_name)
    if editor is None:
        flash("Suite not found.", "danger")
        return redirect(url_for("suite.suites"))
    with connect() as db:
        active = db.execute(
            "SELECT id,status FROM jobs WHERE lower(suite)=lower(?) "
            "AND status IN ('queued','running','cancel_requested') ORDER BY id LIMIT 1",
            (editor["key"],),
        ).fetchone()
    if active:
        flash(f"Cannot delete this suite while job #{active['id']} is {active['status']}.", "warning")
        return redirect(url_for("suite.suites"))
    deleted = delete_suite(editor["key"])
    flash(f"{deleted} suite deleted. Scenario YAML files were preserved.", "success")
    return redirect(url_for("suite.suites"))


def queue_suite(suite_name, mode, module=None):
    editor = get_suite_editor(suite_name)
    if editor is None:
        return None, "Suite not found."
    suite_key = editor["key"]
    if mode not in {"queue", "run-now"}:
        return None, "Invalid execution mode."
    suite_path = ROOT / "Suites" / f"{suite_key}.json"
    suite_data = json.loads(suite_path.read_text(encoding="utf-8"))
    execution_key = suite_key
    if module:
        requested = " ".join(str(module).split()).strip()
        selected = [
            test for test in editor["tests"]
            if str(test.get("display_module") or "").casefold() == requested.casefold()
        ]
        if not selected:
            return None, f"Module {requested or module} has no test cases."
        safe_module = re.sub(r"[^a-z0-9]+", "_", requested.casefold()).strip("_")
        execution_key = f"{suite_key}__module__{safe_module}"
        suite_data = {
            "suite": f"{editor['name']} - {requested}",
            "source_suite": suite_key,
            "module": requested,
            "tests": selected,
        }
        (ROOT / "Suites" / f"{execution_key}.json").write_text(
            json.dumps(suite_data, indent=4, ensure_ascii=False), encoding="utf-8"
        )
    errors = validate_suite_definition(suite_data)
    if errors:
        return None, "Suite validation failed: " + "; ".join(errors)
    job_ids = create_batched_jobs(execution_key, suite_data.get("tests", []), mode)
    return job_ids, None


@suite_bp.route("/run-suite/<suite_name>", methods=["POST"])
@suite_bp.route("/run-suite/<suite_name>/<mode>", methods=["POST"])
def run_selected_suite(suite_name, mode="queue"):
    module = request.form.get("module", "").strip() or None
    job_ids, error = queue_suite(suite_name, mode, module=module)
    if error:
        flash(error, "danger")
        return redirect(url_for("suite.suites"))
    action = "requested to run next" if mode == "run-now" else "added to the queue"
    batch_note = f" in {len(job_ids)} batches" if len(job_ids) > 1 else ""
    scope = f"{module} module" if module else "full suite"
    flash(f"{suite_name.title()} {scope} {action}{batch_note}; first job #{job_ids[0]}.", "success")
    return redirect(url_for("jobs.job_detail", job_id=job_ids[0]))
