import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from web.portal_db import connect
from web.services.yaml_editor_service import validate_maestro_yaml

APPROVABLE = [f"SUB_ACCOUNT_{number:03d}" for number in (1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12)]
SOURCE = "Subscriber_Account_Settings_Approved_Test_Cases.xlsx"


def main():
    approved = []
    with connect() as db:
        drafts = {
            row["case_id"]: row
            for row in db.execute("SELECT * FROM drafts WHERE source_file=?", (SOURCE,)).fetchall()
        }
    for case_id in APPROVABLE:
        yaml_path = ROOT / "Scenarios" / f"{case_id}.yaml"
        yaml_text = yaml_path.read_text(encoding="utf-8")
        if not validate_maestro_yaml(yaml_text):
            raise ValueError(f"Invalid Maestro YAML: {case_id}")
        draft = drafts[case_id]
        traceability = json.loads(draft["traceability"] or "[]")
        for item in traceability:
            item.update(
                status="covered",
                reason="Grounded against ANON_ACCOUNT flows and SC_32 subscriber account flow.",
            )
        with connect() as db:
            db.execute(
                "UPDATE drafts SET yaml=?, traceability=?, coverage_status='complete', "
                "ai_confidence=1, generation_mode='friday-grounded', status='approved', "
                "error=NULL, reviewed_by='Friday', reviewed_at=CURRENT_TIMESTAMP WHERE id=?",
                (yaml_text, json.dumps(traceability), draft["id"]),
            )
        approved.append(case_id)
    with connect() as db:
        phone = drafts["SUB_ACCOUNT_003"]
        db.execute(
            "UPDATE drafts SET status='pending', coverage_status='incomplete', ai_confidence=0, "
            "generation_mode='friday-reviewing', error=? WHERE id=?",
            ("Live phone input locator and non-save behavior must be discovered before safe approval.", phone["id"]),
        )
    print(json.dumps({"approved": approved, "pending": ["SUB_ACCOUNT_003"]}, indent=2))


if __name__ == "__main__":
    main()
