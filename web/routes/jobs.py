import json
import os
from pathlib import Path
from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from web.portal_db import connect
from web.routes.auth import login_required
from web.time_utils import utc_now_text
from web.services.adaptive_test_agent import AdaptiveTestAgent, classify_execution_failure
from web.services.scenario_service import validate_suite_definition
from web.services.job_queue_service import create_batched_jobs
from web.services.result_validation_service import excel_condition_verdict
from web.services.yaml_editor_service import account_tag

ROOT = Path(__file__).resolve().parents[2]
jobs_bp = Blueprint("jobs", __name__)


def agent_authorized():
    expected = os.getenv("MAESTRO_AGENT_TOKEN", "change-me")
    return request.headers.get("X-Agent-Token") == expected


@jobs_bp.route("/jobs")
@login_required
def jobs():
    with connect() as db:
        rows = db.execute(
            """SELECT * FROM jobs
               ORDER BY CASE status WHEN 'running' THEN 0 WHEN 'queued' THEN 1 ELSE 2 END,
                        CASE WHEN status='queued' THEN priority END DESC,
                        CASE WHEN status='queued' THEN id END ASC,
                        id DESC LIMIT 100"""
        ).fetchall()
        next_row = db.execute(
            "SELECT id FROM jobs WHERE status='queued' ORDER BY priority DESC, id ASC LIMIT 1"
        ).fetchone()
    return render_template("jobs.html", jobs=rows, next_job_id=next_row["id"] if next_row else None)


@jobs_bp.route("/jobs/<int:job_id>")
@login_required
def job_detail(job_id):
    with connect() as db:
        job = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        results = db.execute("SELECT * FROM job_results WHERE job_id=? ORDER BY id", (job_id,)).fetchall()
    if not job:
        abort(404)
    passed = [row for row in results if row["status"] == "PASS"]
    needs_review = [row for row in results if row["status"] == "NEEDS_REVIEW"]
    failures = [row for row in results if row["status"] in {"FAIL", "CANCELLED"}]
    return render_template("job_detail.html", job=job, results=results, passed=passed,
                           needs_review=needs_review, failures=failures)


@jobs_bp.route("/jobs/create/<suite>", methods=["POST"])
@login_required
def create_job(suite):
    suite_path = ROOT / "Suites" / f"{suite}.json"
    if not suite_path.exists():
        abort(404)
    suite_data = json.loads(suite_path.read_text(encoding="utf-8"))
    errors = validate_suite_definition(suite_data)
    if errors:
        return jsonify({"error": "Suite validation failed", "details": errors}), 422
    mode = request.args.get("mode", "queue")
    if mode not in {"queue", "run-now"}:
        return jsonify({"error": "invalid mode"}), 400
    job_ids = create_batched_jobs(suite, suite_data.get("tests", []), mode)
    return jsonify({"id": job_ids[0], "job_ids": job_ids, "batches": len(job_ids),
                    "status": "queued", "mode": "run_now" if mode == "run-now" else "queue"}), 201


@jobs_bp.route("/jobs/<int:job_id>/run-next", methods=["POST"])
@login_required
def run_next(job_id):
    with connect() as db:
        job = db.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not job:
            abort(404)
        if job["status"] != "queued":
            flash("Only queued jobs can be moved to next.", "warning")
        else:
            priority = db.execute("SELECT COALESCE(MAX(priority), 0) + 1 FROM jobs WHERE status='queued'").fetchone()[0]
            db.execute("UPDATE jobs SET priority=?,request_mode='run_now' WHERE id=?", (priority, job_id))
            flash(f"Job #{job_id} will run next.", "success")
    return redirect(url_for("jobs.jobs"))


@jobs_bp.route("/jobs/<int:job_id>/cancel", methods=["POST"])
@login_required
def cancel_job(job_id):
    with connect() as db:
        job = db.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not job:
            abort(404)
        if job["status"] == "queued":
            db.execute(
                "UPDATE jobs SET status='cancelled',current_case=NULL,finished_at=CURRENT_TIMESTAMP WHERE id=?",
                (job_id,),
            )
            flash(f"Queued job #{job_id} was cancelled.", "success")
        elif job["status"] == "running":
            db.execute("UPDATE jobs SET status='cancel_requested' WHERE id=?", (job_id,))
            flash(f"Cancellation requested for job #{job_id}.", "warning")
        elif job["status"] == "cancel_requested":
            flash(f"Job #{job_id} is already cancelling.", "warning")
        else:
            flash("Only queued or running jobs can be cancelled.", "warning")
    return redirect(request.referrer or url_for("jobs.jobs"))


@jobs_bp.route("/api/jobs/<int:job_id>")
@login_required
def job_status(job_id):
    with connect() as db:
        row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    return jsonify(dict(row)) if row else (jsonify({"error": "not found"}), 404)


@jobs_bp.route("/api/agent/jobs/claim", methods=["POST"])
def claim_job():
    if not agent_authorized():
        abort(401)
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        job = db.execute(
            "SELECT * FROM jobs WHERE status='queued' ORDER BY priority DESC, id ASC LIMIT 1"
        ).fetchone()
        if not job:
            return jsonify({}), 204
        db.execute("UPDATE jobs SET status='running',started_at=CURRENT_TIMESTAMP,agent=? WHERE id=?",
                   (request.json.get("agent", "local-agent"), job["id"]))
    suite_path = ROOT / "Suites" / f"{job['suite']}.json"
    suite = json.loads(suite_path.read_text(encoding="utf-8"))
    tests = []
    selected_tests = suite.get("tests", [])[job["batch_start"]:job["batch_start"] + job["total"]]
    for test in selected_tests:
        scenario = ROOT / "Scenarios" / test["yaml"]
        item = dict(test)
        item["yaml_content"] = scenario.read_text(encoding="utf-8") if scenario.exists() else ""
        tests.append(item)
    response = dict(job)
    with connect() as db:
        timeout_row = db.execute(
            "SELECT value FROM portal_settings WHERE key='case_timeout_seconds'"
        ).fetchone()
    response["case_timeout_seconds"] = int(timeout_row["value"]) if timeout_row else 300
    response["tests"] = tests
    # Generated scenarios may compose validated modules from Scenarios/. Ship
    # those modules with the job just as we already ship Common flows.
    response["scenario_flows"] = {
        flow.relative_to(ROOT / "Scenarios").as_posix(): flow.read_text(encoding="utf-8")
        for flow in (ROOT / "Scenarios").rglob("*.yaml")
    }
    response["common_flows"] = {
        flow.relative_to(ROOT / "Common").as_posix(): flow.read_text(encoding="utf-8")
        for flow in (ROOT / "Common").rglob("*.yaml")
    }
    return jsonify(response)


@jobs_bp.route("/api/agent/jobs/<int:job_id>/status")
def agent_job_status(job_id):
    if not agent_authorized():
        abort(401)
    with connect() as db:
        job = db.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()
    return jsonify({"status": job["status"]}) if job else (jsonify({"error": "not found"}), 404)


@jobs_bp.route("/api/agent/jobs/<int:job_id>", methods=["PATCH"])
def update_job(job_id):
    if not agent_authorized():
        abort(401)
    payload = request.get_json() or {}
    allowed = {k: payload[k] for k in ("status", "current_case", "completed", "logs", "report_folder") if k in payload}
    if not allowed:
        return jsonify({"error": "no fields"}), 400
    if allowed.get("status") in ("passed", "failed", "needs_review", "cancelled"):
        allowed["finished_at"] = utc_now_text()
    values = list(allowed.values()) + [job_id]
    with connect() as db:
        db.execute(f"UPDATE jobs SET {','.join(f'{key}=?' for key in allowed)} WHERE id=?", values)
    return jsonify({"updated": True})


@jobs_bp.route("/api/agent/jobs/<int:job_id>/results", methods=["POST"])
def add_result(job_id):
    if not agent_authorized():
        abort(401)
    data = request.get_json() or {}
    if "case_id" not in data or "status" not in data:
        return jsonify({"error": "case_id and status are required"}), 400
    final_status, condition_status, condition_details = excel_condition_verdict(
        data["case_id"], data["status"]
    )
    if str(data["status"]).upper() == "FAIL":
        diagnosis = classify_execution_failure(
            f"{data.get('stdout', '')}\n{data.get('stderr', '')}"
        )
        if diagnosis.get("classification") == "PRODUCT_BUG":
            condition_status = "product_bug"
            condition_details = diagnosis.get("root_cause", "Confirmed product defect.")
    yaml_text = ""
    user_state = ""
    with connect() as db:
        job = db.execute("SELECT suite FROM jobs WHERE id=?", (job_id,)).fetchone()
        if job:
            suite_path = ROOT / "Suites" / f"{job['suite']}.json"
            if suite_path.is_file():
                suite = json.loads(suite_path.read_text(encoding="utf-8"))
                test = next((item for item in suite.get("tests", [])
                             if item.get("id") == data["case_id"]), {})
                scenario = ROOT / "Scenarios" / str(test.get("yaml", ""))
                if scenario.is_file():
                    yaml_text = scenario.read_text(encoding="utf-8")
                    user_state = account_tag(test.get("yaml", ""), yaml_text).upper()
        draft = db.execute(
            "SELECT user_state FROM drafts WHERE case_id=? ORDER BY id DESC LIMIT 1",
            (data["case_id"],),
        ).fetchone()
        user_state = draft["user_state"] if draft else user_state
        db.execute(
            """INSERT INTO job_results(
                   job_id,case_id,name,status,duration,stdout,stderr,
                   execution_status,condition_status,condition_details
               ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (job_id, data["case_id"], data.get("name", data["case_id"]), final_status,
             data.get("duration", 0), data.get("stdout", ""), data.get("stderr", ""),
             data["status"], condition_status, condition_details),
        )
    try:
        AdaptiveTestAgent.learn_from_execution(
            data["case_id"], final_status, data.get("stdout", ""), data.get("stderr", ""),
            source=f"job:{job_id}:case:{data['case_id']}",
            yaml_text=yaml_text, name=data.get("name", data["case_id"]),
            user_state=user_state, failure_plan=data.get("failure_plan"),
        )
    except Exception:
        # Learning must never break result reporting.
        pass
    return jsonify({"created": True, "status": final_status,
                    "condition_status": condition_status,
                    "condition_details": condition_details}), 201
