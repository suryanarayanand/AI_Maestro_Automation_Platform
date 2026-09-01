import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from web.routes.suite import queue_suite


if len(sys.argv) != 3:
    raise SystemExit("Usage: queue_suite_module.py <suite> <module>")

job_ids, error = queue_suite(sys.argv[1], "queue", module=sys.argv[2])
if error:
    raise SystemExit(error)
print("queued_jobs=" + ",".join(map(str, job_ids)))
