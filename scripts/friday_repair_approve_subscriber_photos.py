import json

from web.portal_db import connect
from web.services.generation_service import approve_draft
from web.services.testing_bot_service import _repair_proposal_for


SOURCE = "Subscriber_Photos_Quick_Access_Approved_Test_Cases.xlsx"
SUITE = "user_subscriber"


with connect() as db:
    drafts = db.execute(
        "SELECT * FROM drafts WHERE source_file=? AND status='pending' ORDER BY id",
        (SOURCE,),
    ).fetchall()

approved = []
blocked = []
for draft in drafts:
    try:
        proposal = _repair_proposal_for(draft)
        if proposal["coverage"] != 1.0 or proposal["coverage_status"] != "complete":
            raise ValueError("Friday repair did not reach 100% coverage")
        with connect() as db:
            db.execute(
                """UPDATE drafts SET yaml=?,traceability=?,coverage_status='complete',
                   ai_confidence=1.0,generation_mode='friday-repaired',error=NULL WHERE id=?""",
                (proposal["yaml"], proposal["traceability"], draft["id"]),
            )
        approve_draft(draft["id"], proposal["yaml"], SUITE, "friday", False)
        approved.append(draft["case_id"])
    except Exception as exc:
        blocked.append({"case_id": draft["case_id"], "reason": str(exc)})

print(json.dumps({"approved": approved, "blocked": blocked}, indent=2))
