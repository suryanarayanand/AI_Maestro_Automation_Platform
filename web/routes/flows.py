import json
import os
import re
from pathlib import Path

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from web.services.scenario_service import validate_suite_definition
from web.services.yaml_editor_service import list_scenarios
from web.services.job_queue_service import create_batched_jobs


flows_bp = Blueprint("flows", __name__)
ROOT = Path(__file__).resolve().parents[2]
SUITES = ROOT / "Suites"
STATES = (
    ("anonymous", "Anonymous"),
    ("subscriber", "Subscriber"),
    ("registered-user", "Registered user"),
    ("expired-user", "Expired user"),
)


def _suite_key(value):
    key = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(value or "").strip()).strip("_").lower()
    if not key:
        raise ValueError("Enter a suite name.")
    return key


@flows_bp.route("/flows")
def index():
    selected_state = request.args.get("user_state", "anonymous").strip().lower()
    valid_states = {key for key, _ in STATES}
    if selected_state not in valid_states:
        selected_state = "anonymous"
    query = request.args.get("q", "").strip()
    all_flows = list_scenarios(query=query)
    flows = [flow for flow in all_flows if flow["account_tag"] == selected_state]
    counts = {
        state: sum(flow["account_tag"] == state for flow in all_flows)
        for state, _ in STATES
    }
    return render_template("flows.html", flows=flows, states=STATES, counts=counts,
                           selected_state=selected_state, query=query)


@flows_bp.route("/flows/create-suite", methods=["POST"])
def create_suite():
    valid_states = {key for key, _ in STATES}
    user_state = request.form.get("user_state", "").strip().lower()
    if user_state not in valid_states:
        flash("Choose a valid user state.", "danger")
        return redirect(url_for("flows.index"))

    selected = list(dict.fromkeys(request.form.getlist("flows")))
    available = {
        flow["path"]: flow for flow in list_scenarios()
        if flow["account_tag"] == user_state
    }
    unknown = [path for path in selected if path not in available]
    if not selected:
        flash("Select at least one flow.", "warning")
        return redirect(url_for("flows.index", user_state=user_state))
    if unknown:
        flash("One or more selected flows do not belong to that user state.", "danger")
        return redirect(url_for("flows.index", user_state=user_state))

    try:
        key = _suite_key(request.form.get("suite_name"))
        target = SUITES / f"{key}.json"
        if target.exists():
            raise ValueError(f"Suite '{key}' already exists. Choose another name.")
        tests = []
        for path in selected:
            flow = available[path]
            tests.append({
                "id": Path(path).stem,
                "name": Path(path).stem.replace("_", " "),
                "module": flow["folder"] if flow["folder"] != "." else "Flows",
                "priority": "P2",
                "user_state": user_state.upper().replace("-", "_"),
                "yaml": path,
            })
        data = {"suite": key, "user_state": user_state.upper().replace("-", "_"), "tests": tests}
        errors = validate_suite_definition(data)
        if errors:
            raise ValueError("; ".join(errors))
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")
        os.replace(temporary, target)
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("flows.index", user_state=user_state))

    if request.form.get("submit_action") == "run-now":
        job_ids = create_batched_jobs(key, tests, "run-now")
        batch_note = f" in {len(job_ids)} batches" if len(job_ids) > 1 else ""
        flash(
            f"Created {key} with {len(tests)} {dict(STATES)[user_state]} flow(s) "
            f"and started execution{batch_note}.",
            "success",
        )
        return redirect(url_for("jobs.job_detail", job_id=job_ids[0]))

    flash(f"Created {key} with {len(tests)} {dict(STATES)[user_state]} flow(s).", "success")
    return redirect(url_for("suite.edit_suite", suite_name=key))
