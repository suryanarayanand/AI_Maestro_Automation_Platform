import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from web.portal_db import connect
from web.services.job_queue_service import create_batched_jobs


def main():
    parser = argparse.ArgumentParser(description="Create a portal suite containing only failed cases.")
    parser.add_argument("job_id", type=int)
    args = parser.parse_args()
    with connect() as db:
        job = db.execute("SELECT * FROM jobs WHERE id=?", (args.job_id,)).fetchone()
        failed_ids = [row["case_id"] for row in db.execute(
            "SELECT case_id FROM job_results WHERE job_id=? AND status='FAIL' ORDER BY id",
            (args.job_id,),
        )]
    if not job or job["status"] in {"running", "queued", "cancel_requested"}:
        raise SystemExit("The source job must be finished before creating its failed-only rerun.")
    if not failed_ids:
        raise SystemExit("The source job has no failed cases.")
    source = ROOT / "Suites" / f"{job['suite']}.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    failed = set(failed_ids)
    tests = [test for test in data.get("tests", []) if test.get("id") in failed]
    if len(tests) != len(failed):
        raise SystemExit("One or more failed cases are missing from the source suite.")
    key = re.sub(r"[^a-z0-9]+", "_", f"{job['suite']}_failed_{args.job_id}".lower()).strip("_")
    suite = {
        "suite": f"{data.get('suite', job['suite'])} - Failed retry #{args.job_id}",
        "source_suite": job["suite"], "module": data.get("module", ""), "tests": tests,
    }
    (ROOT / "Suites" / f"{key}.json").write_text(
        json.dumps(suite, indent=4, ensure_ascii=False), encoding="utf-8"
    )
    job_ids = create_batched_jobs(key, tests, mode="run-now")
    print(json.dumps({"suite": key, "failed_cases": failed_ids, "job_ids": job_ids}))


if __name__ == "__main__":
    main()
