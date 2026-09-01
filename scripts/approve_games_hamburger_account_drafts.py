from web.portal_db import connect
from web.services.generation_service import approve_draft


SOURCE = "Anonymous_Games_Hamburger_Account_Settings_Approved_Test_Cases.xlsx"
SUITE = "user_anonymous"
with connect() as db:
    rows = db.execute(
        "SELECT id,case_id,yaml FROM drafts WHERE source_file=? AND status='pending' ORDER BY id",
        (SOURCE,),
    ).fetchall()
for row in rows:
    approve_draft(row["id"], row["yaml"], SUITE, "friday-review", allow_incomplete=False)
    print("approved", row["case_id"], "draft", row["id"])
print("approved_total", len(rows))
