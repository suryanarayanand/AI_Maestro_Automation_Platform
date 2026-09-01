import re
import subprocess
from pathlib import Path

from web.portal_db import connect
from web.services.adaptive_test_agent import classify_execution_failure

ROOT = Path(__file__).resolve().parents[2]
REPORT_FOLDER = ROOT / "Reports"
PRIMARY_REPORT_FILES = {
    "AI_Report.html", "AI_Report.json",
    "Bug_Summary.html", "Bug_Summary.json",
    "Dashboard.html", "Dashboard.xlsx",
    "Visual_Report.html", "Visual_Report.json",
}


def get_reports():

    reports = []

    if not REPORT_FOLDER.exists():
        return reports

    folders = sorted(
        REPORT_FOLDER.iterdir(),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )

    for folder in folders:

        if folder.is_dir():

            with connect() as db:
                job = db.execute(
                    "SELECT id,status,completed,total,finished_at FROM jobs WHERE report_folder=? "
                    "ORDER BY id DESC LIMIT 1", (folder.name,),
                ).fetchone()
            reports.append({"name": folder.name, "job": dict(job) if job else None,
                            "status": str(job["status"]).upper() if job else "UNKNOWN"})

    return reports


def get_report_details(report_name):

    report_path = REPORT_FOLDER / report_name

    if not report_path.exists():
        return None

    files = []
    logs = []
    screenshots = []
    screenshot_artifacts = []
    case_folders = []

    cases_root = report_path / "cases"
    if cases_root.is_dir():
        case_folders = [{
            "case_id": folder.name,
            "relative_path": folder.relative_to(report_path).as_posix(),
            "folder_path": str(folder.resolve()),
            "artifact_count": sum(1 for item in folder.rglob("*") if item.is_file()),
        } for folder in sorted(cases_root.iterdir()) if folder.is_dir()]

    artifacts = []
    for item in sorted(report_path.rglob("*")):

        if item.is_file():

            relative = item.relative_to(report_path).as_posix()
            artifacts.append(relative)
            is_screenshot = "screenshots" in {part.lower() for part in item.relative_to(report_path).parts} \
                and item.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"}
            if is_screenshot and (not case_folders or relative.startswith("cases/")):
                screenshot_artifacts.append({
                    "name": item.name,
                    "relative_path": relative,
                    "relative_folder": item.parent.relative_to(report_path).as_posix(),
                    "folder_path": str(item.parent.resolve()),
                })
            elif item.suffix == ".log":
                logs.append(relative)
            elif item.parent == report_path and item.name in PRIMARY_REPORT_FILES:
                files.append(relative)

        elif item.is_dir() and item.name.lower() == "screenshots":
            screenshots.extend(x.name for x in sorted(item.iterdir()))

    with connect() as db:
        job = db.execute("SELECT * FROM jobs WHERE report_folder=? ORDER BY id DESC LIMIT 1",
                         (report_name,)).fetchone()
        results = db.execute("SELECT * FROM job_results WHERE job_id=? ORDER BY id",
                             (job["id"],)).fetchall() if job else []

    def steps_for(row):
        text = "\n".join(filter(None, (row["stdout"], row["stderr"])))
        steps = []
        pattern = re.compile(r"^\s*(.+?)\.\.\.\s*(COMPLETED|FAILED|SKIPPED|RUNNING)\s*$")
        for line in text.splitlines():
            match = pattern.match(line)
            if match and match.group(2) != "RUNNING":
                steps.append({"number": len(steps) + 1, "command": match.group(1).strip(),
                              "status": match.group(2)})
        return steps

    case_results = []
    for row in results:
        item = dict(row); item["steps"] = steps_for(row)
        failure_text = row["stderr"] or row["stdout"] or ""
        item["failure_reason"] = next((line.strip() for line in failure_text.splitlines()
                                       if "FAILED" in line or "Assertion" in line or "Exception" in line), "")
        item["failure_analysis"] = classify_execution_failure(failure_text) \
            if row["status"] != "PASS" else {}
        case_results.append(item)

    metadata = {"app_name": "The Hindu", "package_id": "com.mobstac.thehindu"}
    try:
        device = subprocess.run(["adb", "devices"], capture_output=True, text=True,
                                timeout=5).stdout.splitlines()[1].split()[0]
        def adb(*args):
            return subprocess.run(["adb", "-s", device, *args], capture_output=True,
                                  text=True, timeout=8).stdout.strip()
        package = adb("shell", "dumpsys", "package", metadata["package_id"])
        metadata.update({"device_id": device, "device_model": adb("shell", "getprop", "ro.product.model"),
                         "android_version": adb("shell", "getprop", "ro.build.version.release"),
                         "version_name": (re.search(r"versionName=([^\s]+)", package) or [None, "Unknown"])[1],
                         "version_code": (re.search(r"versionCode=(\d+)", package) or [None, "Unknown"])[1]})
    except Exception:
        metadata.update({"device_id": "Unavailable", "device_model": "Unavailable",
                         "android_version": "Unavailable", "version_name": "Unknown",
                         "version_code": "Unknown"})

    return {
        "name": report_name,
        "files": files,
        "logs": logs,
        "screenshots": sorted(set(screenshots)),
        "screenshot_artifacts": screenshot_artifacts,
        "case_folders": case_folders,
        "artifacts": artifacts,
        "job": dict(job) if job else None, "results": case_results, "metadata": metadata,
    }
