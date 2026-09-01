import argparse
import json
from pathlib import Path

from web.services.job_queue_service import create_batched_jobs


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description="Queue an existing portal suite.")
    parser.add_argument("suite")
    parser.add_argument("--mode", choices=("queue", "run-now"), default="run-now")
    args = parser.parse_args()
    path = ROOT / "Suites" / f"{args.suite}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    tests = data.get("tests", [])
    if not tests:
        raise SystemExit("Suite has no tests.")
    ids = create_batched_jobs(args.suite, tests, mode=args.mode)
    print(json.dumps({"suite": args.suite, "tests": len(tests), "job_ids": ids}))


if __name__ == "__main__":
    main()
