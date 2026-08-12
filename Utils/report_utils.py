from pathlib import Path
from datetime import datetime


def get_timestamp():
    """Return current timestamp."""
    return datetime.now().strftime("%d-%m-%Y %H:%M:%S")


def calculate_statistics(results):
    """Calculate execution statistics."""

    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    not_found = sum(1 for r in results if r["status"] == "NOT FOUND")

    pass_rate = round((passed / total) * 100, 2) if total else 0

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "not_found": not_found,
        "pass_rate": pass_rate
    }


def create_execution_folder(report_root, suite_name):
    """
    Creates:
    Reports/
        Smoke_20260629_151210/
    """

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    folder = Path(report_root) / f"{suite_name}_{timestamp}"

    folder.mkdir(parents=True, exist_ok=True)

    return folder


def save_log(folder, scenario_id, stdout, stderr):

    folder = Path(folder)
    # The report directory may be removed or not yet materialized when an
    # execution is cancelled while the agent is collecting its final output.
    # Log persistence must not crash the agent or strand the portal job.
    folder.mkdir(parents=True, exist_ok=True)
    log_file = folder / f"{scenario_id}.log"

    with open(log_file, "w", encoding="utf-8") as f:

        f.write("===== STDOUT =====\n\n")
        f.write(stdout)

        f.write("\n\n")

        f.write("===== STDERR =====\n\n")
        f.write(stderr)

    return log_file
