import json
import os
from pathlib import Path
from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from web.portal_db import connect
from web.routes.auth import login_required
from web.time_utils import utc_now_text

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
    failures = [row for row in results if row["status"] != "PASS"]
    return render_template("job_detail.html", job=job, results=results, failures=failures)


@jobs_bp.route("/jobs/create/<suite>", methods=["POST"])
@login_required
def create_job(suite):
    suite_path = ROOT / "Suites" / f"{suite}.json"
    if not suite_path.exists():
        abort(404)
    total = len(json.loads(suite_path.read_text(encoding="utf-8")).get("tests", []))
    mode = request.args.get("mode", "queue")
    if mode not in {"queue", "run-now"}:
        return jsonify({"error": "invalid mode"}), 400
    with connect() as db:
        priority = 0
        request_mode = "queue"
        if mode == "run-now":
            priority = db.execute("SELECT COALESCE(MAX(priority), 0) + 1 FROM jobs WHERE status='queued'").fetchone()[0]
            request_mode = "run_now"
        cursor = db.execute(
            "INSERT INTO jobs(suite,total,priority,request_mode) VALUES(?,?,?,?)",
            (suite, total, priority, request_mode),
        )
        job_id = cursor.lastrowid
    return jsonify({"id": job_id, "status": "queued", "mode": request_mode}), 201


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
    for test in suite.get("tests", []):
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
    response["common_flows"] = {
        flow.name: flow.read_text(encoding="utf-8")
        for flow in (ROOT / "Common").glob("*.yaml")
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
    if allowed.get("status") in ("passed", "failed", "cancelled"):
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
    with connect() as db:
        db.execute("INSERT INTO job_results(job_id,case_id,name,status,duration,stdout,stderr) VALUES(?,?,?,?,?,?,?)",
                   (job_id, data["case_id"], data.get("name", data["case_id"]), data["status"],
                    data.get("duration", 0), data.get("stdout", ""), data.get("stderr", "")))
    return jsonify({"created": True}), 201
