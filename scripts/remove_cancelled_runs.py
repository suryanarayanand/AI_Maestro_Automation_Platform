import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "portal.db"
REPORTS = ROOT / "Reports"


def main():
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive = ROOT / ".runtime" / "cancelled-run-archive" / stamp
    archive.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DB_PATH, archive / "portal.db.backup")

    with sqlite3.connect(DB_PATH) as db:
        rows = db.execute(
            "SELECT id, report_folder FROM jobs WHERE status='cancelled' ORDER BY id"
        ).fetchall()
        job_ids = [row[0] for row in rows]
        report_folders = [row[1] for row in rows if row[1]]
        if job_ids:
            placeholders = ",".join("?" for _ in job_ids)
            db.execute(f"DELETE FROM job_results WHERE job_id IN ({placeholders})", job_ids)
            db.execute(f"DELETE FROM jobs WHERE id IN ({placeholders})", job_ids)

    moved = []
    reports_root = REPORTS.resolve()
    for folder in report_folders:
        source = (REPORTS / folder).resolve()
        if source.parent != reports_root or not source.is_dir():
            continue
        destination = archive / source.name
        if destination.exists():
            destination = archive / f"{source.name}_{len(moved) + 1}"
        shutil.move(str(source), str(destination))
        moved.append(source.name)

    print(f"removed_cancelled_jobs={len(job_ids)} ids={job_ids}")
    print(f"archived_report_folders={moved}")
    print(f"backup={archive}")


if __name__ == "__main__":
    main()
