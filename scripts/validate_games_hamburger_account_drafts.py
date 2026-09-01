from pathlib import Path

from web.portal_db import connect
from web.services.yaml_editor_service import validate_maestro_yaml


source = "Anonymous_Games_Hamburger_Account_Settings_Approved_Test_Cases.xlsx"
with connect() as db:
    rows = db.execute(
        "SELECT case_id,yaml,error,coverage_status FROM drafts WHERE source_file=? ORDER BY id",
        (source,),
    ).fetchall()
failures = []
for row in rows:
    try:
        scenario = Path("Scenarios") / f"{row['case_id']}.yaml"
        content = scenario.read_text(encoding="utf-8") if scenario.is_file() else row["yaml"]
        valid = validate_maestro_yaml(content)
    except Exception as exc:
        failures.append((row["case_id"], str(exc)))
        continue
    if not valid:
        failures.append((row["case_id"], "validator returned false"))
print({"drafts": len(rows), "syntax_failures": failures,
       "generation_errors": sum(bool(row["error"]) for row in rows),
       "complete": sum(row["coverage_status"] == "complete" for row in rows)})
if failures:
    raise SystemExit(1)
