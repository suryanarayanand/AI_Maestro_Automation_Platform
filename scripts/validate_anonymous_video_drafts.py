import json

from web.portal_db import connect
from web.services.adaptive_test_agent import reusable_yaml
from web.services.yaml_editor_service import validate_maestro_yaml


SOURCE = "Anonymous_Videos_Quick_Section_Approved_Test_Cases.xlsx"
with connect() as db:
    rows = db.execute(
        "SELECT case_id,yaml,traceability,coverage_status,error,status FROM drafts "
        "WHERE source_file=? ORDER BY case_id", (SOURCE,),
    ).fetchall()

assert len(rows) == 16, len(rows)
requirements = covered = 0
for row in rows:
    validate_maestro_yaml(row["yaml"])
    assert reusable_yaml(row["yaml"]), row["case_id"]
    assert row["yaml"].startswith("appId: com.mobstac.thehindu"), row["case_id"]
    traceability = json.loads(row["traceability"] or "[]")
    assert traceability and all(item.get("status") == "covered" for item in traceability), row["case_id"]
    assert row["coverage_status"] == "complete" and not row["error"], row["case_id"]
    assert row["status"] == "pending", row["case_id"]
    requirements += len(traceability)
    covered += sum(item.get("status") == "covered" for item in traceability)

print({"cases": len(rows), "yaml_parse": len(rows), "requirements": requirements,
       "covered": covered, "coverage": covered / requirements, "status": "pending_review"})
