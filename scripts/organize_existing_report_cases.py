import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from web.portal_db import connect


if len(sys.argv) != 2:
    raise SystemExit("Usage: organize_existing_report_cases.py <job-id>")
job_id = int(sys.argv[1])
with connect() as db:
    job = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    results = db.execute(
        "SELECT case_id FROM job_results WHERE job_id=? ORDER BY id", (job_id,)
    ).fetchall()
if not job or not job["report_folder"]:
    raise SystemExit(f"Job {job_id} has no report folder yet")

report = ROOT / "Reports" / job["report_folder"]
for row in results:
    case_id = row["case_id"]
    case_root = report / "cases" / case_id
    sources = {
        "screenshots": list((report / "screenshots" / case_id).rglob("*"))
            if (report / "screenshots" / case_id).is_dir() else [],
        "video": [report / "videos" / f"{case_id}.mp4"],
        "logs": [report / f"{case_id}.log"],
        "failure": [report / "failure_plans" / f"{case_id}.json"],
    }
    manifest = {"case_id": case_id, "folders": {}, "artifacts": []}
    for folder, candidates in sources.items():
        copied = []
        for source in candidates:
            if not source.is_file():
                continue
            destination = case_root / folder
            destination.mkdir(parents=True, exist_ok=True)
            target = destination / source.name
            shutil.copy2(source, target)
            relative = target.relative_to(report).as_posix()
            copied.append(relative)
            manifest["artifacts"].append(relative)
        manifest["folders"][folder] = copied
    case_root.mkdir(parents=True, exist_ok=True)
    (case_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(case_id, len(manifest["artifacts"]), "artifacts")

print("report", report)
