import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from web.portal_db import connect
from web.services.generation_service import approve_draft


SOURCE = "Anonymous_Photos_Quick_Access_Approved_Test_Cases.xlsx"
with connect() as db:
    rows = db.execute(
        "SELECT id, case_id, yaml FROM drafts "
        "WHERE source_file=? AND status='pending' ORDER BY case_id",
        (SOURCE,),
    ).fetchall()

if len(rows) != 14:
    raise SystemExit(f"Expected 14 pending Photos drafts, found {len(rows)}")

for row in rows:
    approve_draft(
        row["id"], row["yaml"], "user_anonymous", "friday-reviewed-live",
        allow_incomplete=False,
    )
    print("approved", row["case_id"], "draft", row["id"])

print("approved_total", len(rows))
