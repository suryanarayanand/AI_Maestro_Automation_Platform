import json

from web.portal_db import connect


case_id = "ANON_PHOTO_010"
reason = (
    "Accuracy audit: YAML assumes a qualifying gallery is already open, but the Excel "
    "precondition starts from the installed app. Deterministic gallery navigation and a "
    "validated READ LESS selector are not yet grounded."
)
with connect() as db:
    row = db.execute(
        "SELECT id,status,generation_mode FROM drafts WHERE case_id=? ORDER BY id DESC LIMIT 1",
        (case_id,),
    ).fetchone()
    if not row or row["status"] != "pending":
        raise SystemExit("pending draft not found")
    db.execute(
        """UPDATE drafts SET coverage_status='incomplete',ai_confidence=0,
           generation_mode='accuracy-audit-blocked',error=?,ai_assumptions=? WHERE id=?""",
        (reason, json.dumps([reason]), row["id"]),
    )
print({"case_id": case_id, "coverage_status": "incomplete", "reason": reason})
