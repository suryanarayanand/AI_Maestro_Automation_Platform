import argparse

from web.portal_db import connect


parser = argparse.ArgumentParser()
parser.add_argument("case_id")
args = parser.parse_args()
with connect() as db:
    row = db.execute(
        "SELECT * FROM drafts WHERE case_id=? ORDER BY id DESC LIMIT 1",
        (args.case_id,),
    ).fetchone()
if not row:
    raise SystemExit("draft not found")
for key in ("id", "case_id", "name", "status", "coverage_status", "generation_mode", "error", "yaml", "traceability", "ai_assumptions"):
    print(f"\n## {key}\n{row[key]}")
