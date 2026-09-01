import json
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from Utils.screenshot_utils import get_screenshots
from Utils.openai_analyzer import analyze_image
from Utils.friday_visual_context import build_friday_visual_context


def analyze_scenario(screenshot_folder, execution_folder, test_id):
    """
    Analyze every screenshot inside one scenario's folder.

    Each screenshot is copied into:
        <execution_folder>/screenshots/<test_id>/<image_name>
    so the HTML report can display it with a plain relative <img src>.

    Parameters:
        screenshot_folder : Folder containing the scenario's screenshots
        execution_folder  : Root report folder for this suite run
        test_id            : Scenario id (e.g. "SC_68"), used to namespace
                              the copied screenshots and as a report key

    Returns:
        dict with total/passed/failed/errors counts and a "details" list.
        Each item in "details" is the raw AI analysis result (status,
        confidence, severity, reason, issues, jira_title, jira_description)
        plus "image" (filename) and "image_path" (relative path for <img>).
    """

    screenshot_folder = Path(screenshot_folder)
    execution_folder = Path(execution_folder)

    dest_folder = execution_folder / "screenshots" / test_id
    dest_folder.mkdir(parents=True, exist_ok=True)

    screenshots = get_screenshots(screenshot_folder)

    details = []
    friday_context = build_friday_visual_context(test_id)
    prepared = []

    for image in screenshots:

        print(f"Analyzing {image.name}...")

        # Copy the screenshot next to the report so the HTML <img> tag
        # can resolve it with a relative path (report stays portable).
        relative_image = image.relative_to(screenshot_folder)
        dest_image = dest_folder / relative_image
        dest_image.parent.mkdir(parents=True, exist_ok=True)
        if image.resolve() != dest_image.resolve():
            shutil.copy2(image, dest_image)
        image_context = dict(friday_context)
        image_context["screenshot_checkpoint"] = image.name
        prepared.append((
            image,
            image_context,
            (Path("screenshots") / test_id / relative_image).as_posix(),
        ))

    # Visual checkpoints are independent. A small bounded pool reduces report
    # latency without changing Maestro execution, test state, or result order.
    try:
        requested_workers = int(os.getenv("AI_SCREENSHOT_WORKERS", "3"))
    except ValueError:
        requested_workers = 3
    worker_count = max(1, min(requested_workers, 4, len(prepared) or 1))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        analyses = list(executor.map(
            lambda item: analyze_image(item[0], item[1]),
            prepared,
        ))

    for (image, _, image_path), result in zip(prepared, analyses):
        result["image"] = image.name
        result["image_path"] = image_path
        details.append(result)

    passed = sum(result.get("status") == "PASS" for result in details)
    failed = sum(result.get("status") == "FAIL" for result in details)
    errors = len(details) - passed - failed

    return {
        "total": len(details),
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "details": details
    }


def analyze_execution(results):
    """
    Creates the suite-level AI summary.

    `results` is the list of per-test dicts built in run_suite.py. Each
    dict is expected to already carry ai_pass / ai_fail / ai_errors /
    ai_details (populated during the run, or zeroed/empty for scenarios
    with no screenshots).
    """

    total = len(results)

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    not_found = sum(1 for r in results if r["status"] == "NOT FOUND")

    pass_rate = round((passed / total) * 100, 2) if total else 0

    return {
        "suite": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "not_found": not_found,
            "pass_rate": pass_rate
        },
        "results": results
    }


def save_ai_report(summary, execution_folder):
    """
    Persists the full AI summary (suite totals + per-test ai_details,
    including per-image reason/issues/image_path) to AI_Report.json.
    This is the ONLY place that writes AI_Report.json, so nothing
    overwrites the detailed per-image data.
    """

    execution_folder = Path(execution_folder)
    report_file = execution_folder / "AI_Report.json"

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4, ensure_ascii=False)

    return report_file
