import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from web.portal_db import connect
from web.services.job_queue_service import create_batched_jobs


TERMINAL = {"completed", "passed", "failed", "needs_review", "cancelled"}


def main():
    parser = argparse.ArgumentParser(
        description="Build one rerun suite from non-pass and unexecuted cases across jobs."
    )
    parser.add_argument("source_suite", help="Canonical suite whose ordering is preserved")
    parser.add_argument("job_ids", nargs="+", type=int)
    parser.add_argument("--key", help="Output suite key")
    parser.add_argument("--queue", action="store_true", help="Queue the suite in run-now mode")
    args = parser.parse_args()

    source_path = ROOT / "Suites" / f"{args.source_suite}.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    source_tests = source.get("tests", [])
    canonical = {test["id"]: test for test in source_tests}

    selected_ids = set()
    evidence = {}
    with connect() as db:
        for job_id in args.job_ids:
            job = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            if not job:
                raise SystemExit(f"Job {job_id} does not exist.")
            if job["status"] not in TERMINAL:
                raise SystemExit(f"Job {job_id} is still {job['status']}.")

            module_path = ROOT / "Suites" / f"{job['suite']}.json"
            module_data = json.loads(module_path.read_text(encoding="utf-8"))
            module_ids = [test["id"] for test in module_data.get("tests", [])]
            results = {
                row["case_id"]: row
                for row in db.execute(
                    "SELECT case_id,status,execution_status,condition_status FROM job_results "
                    "WHERE job_id=? ORDER BY id",
                    (job_id,),
                )
            }
            for case_id in module_ids:
                result = results.get(case_id)
                if result is None or str(result["status"]).upper() != "PASS":
                    selected_ids.add(case_id)
                    evidence[case_id] = {
                        "job_id": job_id,
                        "status": result["status"] if result else "NOT_EXECUTED",
                        "execution_status": result["execution_status"] if result else "",
                        "condition_status": result["condition_status"] if result else "",
                    }

    missing = sorted(selected_ids - canonical.keys())
    if missing:
        raise SystemExit("Cases missing from canonical suite: " + ", ".join(missing))
    tests = [test for test in source_tests if test["id"] in selected_ids]
    key = args.key or re.sub(
        r"[^a-z0-9]+", "_", f"{args.source_suite}_cumulative_nonpass".lower()
    ).strip("_")
    output = {
        "suite": f"{source.get('suite', args.source_suite)} - Cumulative non-pass rerun",
        "source_suite": args.source_suite,
        "source_jobs": args.job_ids,
        "tests": tests,
    }
    (ROOT / "Suites" / f"{key}.json").write_text(
        json.dumps(output, indent=4, ensure_ascii=False), encoding="utf-8"
    )
    result = {"suite": key, "case_count": len(tests), "evidence": evidence}
    if args.queue:
        result["job_ids"] = create_batched_jobs(key, tests, mode="run-now")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
