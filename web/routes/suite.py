import json
from pathlib import Path
from flask import Blueprint, render_template, redirect, url_for, flash, request

from web.services.scenario_service import delete_suite, get_all_suites, get_suite_editor, save_suite_tests
from web.portal_db import connect

suite_bp = Blueprint("suite", __name__)
ROOT = Path(__file__).resolve().parents[2]


@suite_bp.route("/suites")
def suites():
    return render_template(
        "scenarios.html",
        suites=get_all_suites()
    )


@suite_bp.route("/suites/<suite_name>/edit", methods=["GET", "POST"])
def edit_suite(suite_name):
    editor = get_suite_editor(suite_name)
    if editor is None:
        flash("Suite not found.", "danger")
        return redirect(url_for("suite.suites"))
    if request.method == "POST":
        try:
            count = save_suite_tests(editor["key"], request.form.getlist("tests"))
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


def queue_suite(suite_name, mode):
    editor = get_suite_editor(suite_name)
    if editor is None:
        return None, "Suite not found."
    suite_key = editor["key"]
    if mode not in {"queue", "run-now"}:
        return None, "Invalid execution mode."
    suite_path = ROOT / "Suites" / f"{suite_key}.json"
    total = len(json.loads(suite_path.read_text(encoding="utf-8")).get("tests", []))
    with connect() as db:
        priority = 0
        request_mode = "queue"
        if mode == "run-now":
            priority = db.execute("SELECT COALESCE(MAX(priority), 0) + 1 FROM jobs WHERE status='queued'").fetchone()[0]
            request_mode = "run_now"
        cursor = db.execute(
            "INSERT INTO jobs(suite,total,priority,request_mode) VALUES(?,?,?,?)",
            (suite_key, total, priority, request_mode),
        )
        job_id = cursor.lastrowid
    return job_id, None


@suite_bp.route("/run-suite/<suite_name>", methods=["POST"])
@suite_bp.route("/run-suite/<suite_name>/<mode>", methods=["POST"])
def run_selected_suite(suite_name, mode="queue"):
    job_id, error = queue_suite(suite_name, mode)
    if error:
        flash(error, "danger")
        return redirect(url_for("suite.suites"))
    action = "requested to run next" if mode == "run-now" else "added to the queue"
    flash(f"{suite_name.title()} suite {action} as job #{job_id}.", "success")
    return redirect(url_for("jobs.job_detail", job_id=job_id))
