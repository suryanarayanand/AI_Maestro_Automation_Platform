import json
from pathlib import Path
from web.services.device_service import get_device_status
from web.portal_db import connect
# Project root (Automation_Framework_UI)
ROOT = Path(__file__).resolve().parents[2]


def get_dashboard_stats():
    """
    Collect dashboard statistics from the framework folders.
    """

    suites_folder = ROOT / "Suites"
    scenarios_folder = ROOT / "Scenarios"
    reports_folder = ROOT / "Reports"

    suite_count = len(list(suites_folder.glob("*.json")))

    active_case_keys = set()
    for suite_path in suites_folder.glob("*.json"):
        try:
            tests = json.loads(suite_path.read_text(encoding="utf-8")).get("tests", [])
        except (OSError, json.JSONDecodeError):
            continue
        for test in tests:
            if not isinstance(test, dict):
                continue
            identity = test.get("id") or test.get("yaml")
            if identity:
                active_case_keys.add(str(identity).casefold())
    scenario_count = len(active_case_keys)

    report_count = len(
        [
            folder
            for folder in reports_folder.iterdir()
            if folder.is_dir()
        ]
    )
    device = get_device_status()
    with connect() as db:
        pending_drafts = db.execute(
            "SELECT COUNT(*) FROM drafts WHERE status='pending'"
        ).fetchone()[0]
        active_jobs = db.execute(
            "SELECT COUNT(*) FROM jobs WHERE status IN ('queued','running','cancel_requested')"
        ).fetchone()[0]
        latest_jobs = db.execute(
            "SELECT * FROM jobs ORDER BY id DESC LIMIT 5"
        ).fetchall()
        latest_completed = db.execute(
            "SELECT * FROM jobs WHERE status IN ('passed','failed','needs_review','cancelled') "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()

    return {
        "suite_count": suite_count,
        "scenario_count": scenario_count,
        "report_count": report_count,
        "device_status": device["status"],
        "pending_drafts": pending_drafts,
        "active_jobs": active_jobs,
        "latest_jobs": latest_jobs,
        "latest_completed": latest_completed,
    }
