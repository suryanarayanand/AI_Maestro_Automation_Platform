from flask import Blueprint, jsonify, render_template
from Utils.unique_bug_summary import generate_unique_bug_summary

from web.services.report_service import (
    get_reports,
    get_report_details
)
from flask import send_from_directory, abort
from pathlib import Path

report_bp = Blueprint("report", __name__)


@report_bp.route("/reports")
def reports():

    return render_template(
        "reports.html",
        reports=get_reports()
    )


@report_bp.route("/reports/unique-bugs")
def unique_bugs():
    return render_template(
        "unique_bugs.html",
        report=generate_unique_bug_summary(REPORT_FOLDER),
    )


@report_bp.route("/reports/unique-bugs.json")
def unique_bugs_json():
    return jsonify(generate_unique_bug_summary(REPORT_FOLDER))


@report_bp.route("/reports/<report_name>")
def report_details(report_name):

    report = get_report_details(report_name)

    return render_template(
        "report_detail.html",
        report=report
    )

ROOT = Path(__file__).resolve().parents[2]
REPORT_FOLDER = ROOT / "Reports"


@report_bp.route("/reports/<report_name>/file/<path:filename>")
def open_report_file(report_name, filename):

    report_path = REPORT_FOLDER / report_name

    file_path = report_path / filename

    if not file_path.exists():
        abort(404)

    return send_from_directory(
        report_path,
        filename
    )


