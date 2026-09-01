"""Re-index repository resources and backfill learning from historical runs."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from web.portal_db import connect, init_db
from web.services.app_memory_service import rebuild_memory


init_db()
print(rebuild_memory())
with connect() as db:
    print(dict(db.execute(
        """SELECT COUNT(*) flows,
                  SUM(CASE WHEN pass_count>0 THEN 1 ELSE 0 END) passed_flows,
                  SUM(CASE WHEN fail_count>0 THEN 1 ELSE 0 END) failed_flows
           FROM app_memory_flows"""
    ).fetchone()))
    print([
        dict(row) for row in db.execute(
            """SELECT observation_type,status,COUNT(*) count
               FROM app_memory_learning GROUP BY observation_type,status
               ORDER BY observation_type,status"""
        )
    ])
