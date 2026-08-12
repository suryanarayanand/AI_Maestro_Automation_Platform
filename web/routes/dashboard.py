from flask import Blueprint, render_template, jsonify

from web.services.dashboard_service import get_dashboard_stats

from web.portal_db import connect
from web.time_utils import portal_time
dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def dashboard():

    stats = get_dashboard_stats()

    return render_template(
        "dashboard.html",
        stats=stats
    )


@dashboard_bp.route("/execution-status")
def execution_status():
    with connect() as db:
        job = db.execute(
            "SELECT * FROM jobs WHERE status IN ('running','cancel_requested','queued') "
            "ORDER BY CASE status WHEN 'running' THEN 0 WHEN 'cancel_requested' THEN 1 ELSE 2 END, id LIMIT 1"
        ).fetchone()
    if not job:
        return jsonify({"running": False, "status": "idle", "suite": None,
                        "start_time": None, "completed": 0, "total": 0})
    return jsonify({"running": job["status"] in ("running", "cancel_requested"), "status": job["status"],
                    "suite": job["suite"], "start_time": portal_time(job["started_at"]),
                    "completed": job["completed"], "total": job["total"],
                    "job_id": job["id"]})

@dashboard_bp.route("/execution-logs")
def execution_logs():
    with connect() as db:
        job = db.execute("SELECT logs FROM jobs ORDER BY id DESC LIMIT 1").fetchone()
    return jsonify(job["logs"].splitlines()[-200:] if job and job["logs"] else [])
