import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from web.portal_db import connect
from web.services.generation_service import create_drafts


WORKBOOK = ROOT / "Uploads" / "Ready" / "Anonymous_Editorial_Quick_Access_Approved_Test_Cases.xlsx"
SOURCE = WORKBOOK.name

with connect() as db:
    existing = db.execute(
        "SELECT id, case_id, status FROM drafts WHERE source_file=? ORDER BY id", (SOURCE,)
    ).fetchall()

if existing:
    print(f"existing={len(existing)}")
    for row in existing:
        print(row["id"], row["case_id"], row["status"])
else:
    ids, normalization = create_drafts(WORKBOOK, use_ai=True)
    print(
        f"created={len(ids)} cases={normalization.case_count} "
        f"steps={normalization.step_count} sheets={normalization.sheet_count}"
    )
    print("draft_ids=" + ",".join(map(str, ids)))
