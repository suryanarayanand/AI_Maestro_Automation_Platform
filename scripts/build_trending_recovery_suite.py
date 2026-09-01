import json
import sqlite3
from pathlib import Path

JOB_ID = 272
root = Path(__file__).resolve().parents[1]
source_path = root / "Suites" / "user_anonymous.json"
output_path = root / "Suites" / "anonymous_trending_failed_remaining.json"

source = json.loads(source_path.read_text(encoding="utf-8"))
trending = [test for test in source["tests"] if test.get("module") == "Trending"]

db = sqlite3.connect(root / "portal.db")
db.row_factory = sqlite3.Row
results = {
    row["case_id"]: row["status"]
    for row in db.execute(
        "SELECT case_id,status FROM job_results WHERE job_id=? ORDER BY id", (JOB_ID,)
    )
}
db.close()

selected = [
    test for test in trending
    if results.get(test["id"]) in {"FAIL", "CANCELLED"} or test["id"] not in results
]
payload = {
    "suite": "Anonymous Trending - Failed and Remaining",
    "source_suite": "user_anonymous",
    "source_job": JOB_ID,
    "module": "Trending",
    "tests": selected,
}
output_path.write_text(json.dumps(payload, indent=4), encoding="utf-8")
print("selected", len(selected))
for test in selected:
    print(test["id"], results.get(test["id"], "NOT_RUN"))
