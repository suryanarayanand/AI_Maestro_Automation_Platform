import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from web.portal_db import connect

with connect() as db:
    jobs = db.execute(
        "SELECT * FROM jobs ORDER BY id DESC LIMIT 12"
    ).fetchall()
    active = db.execute(
        "SELECT * FROM jobs WHERE status IN ('queued','running','cancel_requested') ORDER BY id"
    ).fetchall()
    for label, rows in (("active", active), ("latest", jobs)):
        print(label)
        for row in rows:
            value = dict(row)
            for key in ("payload", "metadata"):
                if key in value and value[key] and len(str(value[key])) > 500:
                    value[key] = str(value[key])[:500] + "..."
            print(json.dumps(value, default=str))
