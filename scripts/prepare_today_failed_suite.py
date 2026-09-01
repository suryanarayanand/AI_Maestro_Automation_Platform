"""Build a deduplicated rerun suite from today's failed portal results."""

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from web.portal_db import connect


with connect() as db:
    active = db.execute("SELECT * FROM jobs WHERE id=232").fetchone()
    rows = db.execute(
        """SELECT r.case_id,r.name,r.status,r.execution_status,r.job_id,j.suite,r.created_at
           FROM job_results r JOIN jobs j ON j.id=r.job_id
           WHERE r.id IN (
               SELECT MAX(id) FROM job_results
               WHERE date(created_at)=date('now') GROUP BY case_id
           ) AND r.execution_status='FAIL'
           ORDER BY r.id DESC"""
    ).fetchall()

print("job_232", dict(active) if active else None)
all_tests = {}
for available_suite in (ROOT / "Suites").glob("*.json"):
    try:
        for item in json.loads(available_suite.read_text(encoding="utf-8")).get("tests", []):
            all_tests.setdefault(item.get("id"), dict(item))
    except (OSError, json.JSONDecodeError):
        continue
selected = []
seen = set()
for row in rows:
    if row["case_id"] in seen:
        continue
    seen.add(row["case_id"])
    suite_path = ROOT / "Suites" / f"{row['suite']}.json"
    try:
        tests = json.loads(suite_path.read_text(encoding="utf-8")).get("tests", [])
    except (OSError, json.JSONDecodeError):
        tests = []
    test = next((item for item in tests if item.get("id") == row["case_id"]), None)
    test = test or all_tests.get(row["case_id"])
    if not test:
        matches = sorted((ROOT / "Scenarios").rglob(f"{row['case_id']}_*.yaml"))
        if matches:
            test = {
                "id": row["case_id"], "name": row["name"] or row["case_id"],
                "module": "Recovered failed cases", "priority": "P1",
                "yaml": matches[0].relative_to(ROOT / "Scenarios").as_posix(),
            }
    if test and (ROOT / "Scenarios" / str(test.get("yaml", ""))).is_file():
        selected.append(dict(test))
        print("selected", row["case_id"], row["suite"], test["yaml"])
    else:
        print("skipped_missing_yaml", row["case_id"], row["suite"])

output = ROOT / "Suites" / "today_failed_confirmation.json"
output.write_text(json.dumps({
    "suite": f"Today Failed Confirmation {datetime.now():%Y-%m-%d}",
    "tests": selected,
}, indent=2) + "\n", encoding="utf-8")
print("failures", len(seen), "runnable", len(selected), "suite", output)
