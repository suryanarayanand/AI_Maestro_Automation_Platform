import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from web.routes.suite import queue_suite


job_ids, error = queue_suite(
    "user_anonymous", "run-now", module="Videos Quick Access"
)
if error:
    raise SystemExit(error)
print("queued_jobs=" + ",".join(map(str, job_ids)))
