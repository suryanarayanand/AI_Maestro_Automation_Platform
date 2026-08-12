from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT_FOLDER = ROOT / "Reports"


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

            reports.append({
                "name": folder.name
            })

    return reports


def get_report_details(report_name):

    report_path = REPORT_FOLDER / report_name

    if not report_path.exists():
        return None

    files = []
    logs = []
    screenshots = []

    for item in sorted(report_path.iterdir()):

        if item.is_file():

            if item.suffix == ".log":
                logs.append(item.name)
            else:
                files.append(item.name)

        elif item.is_dir() and item.name == "screenshots":

            for folder in sorted(item.iterdir()):
                screenshots.append(folder.name)

    return {
        "name": report_name,
        "files": files,
        "logs": logs,
        "screenshots": screenshots
    }