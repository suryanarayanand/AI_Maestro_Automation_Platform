import sqlite3

from web.services.generation_service import approve_draft

SOURCES = (
    "Anonymous_Premium_Approved_Test_Cases.xlsx",
    "Anonymous_EBooks_Approved_Test_Cases.xlsx",
)

db = sqlite3.connect("portal.db")
db.row_factory = sqlite3.Row
rows = db.execute(
    "SELECT id,case_id,yaml,source_file FROM drafts "
    "WHERE status='pending' AND source_file IN (?,?) ORDER BY source_file,id",
    SOURCES,
).fetchall()
db.close()

approved = []
for row in rows:
    check = sqlite3.connect("portal.db")
    status = check.execute("SELECT status FROM drafts WHERE id=?", (row["id"],)).fetchone()
    check.close()
    if not status or status[0] != "pending":
        continue
    try:
        approve_draft(
            row["id"], row["yaml"], "user_anonymous",
            reviewer="Codex - user requested bulk approval",
        )
    except ValueError as exc:
        if "not pending" not in str(exc):
            raise
        continue
    approved.append(row["case_id"])

print("approved", len(approved))
print("first", approved[0] if approved else "-", "last", approved[-1] if approved else "-")
