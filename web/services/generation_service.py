import json
import re
import sys
from types import SimpleNamespace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GENERATION = ROOT / "generation"
if str(GENERATION) not in sys.path:
    sys.path.insert(0, str(GENERATION))

from excel_reader import ExcelReader
from yaml_generator import YAMLGenerator
from convert_to_supported_excel import convert as convert_to_supported_excel
from web.portal_db import connect


def _ai_rewrite(case):
    """Ground one unsupported case against repository assets using structured AI output."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from AI.ai_scenario_expander import AIScenarioExpander

    return AIScenarioExpander().expand({
        "test_case_id": case["id"], "name": case["name"],
        "module": "Unassigned", "validation_points": list(case["steps"]),
    })


def create_drafts(excel_path, use_ai=True):
    normalized_folder = ROOT / "Uploads" / "Normalized"
    normalized_path = normalized_folder / f"{Path(excel_path).stem}_normalized.xlsx"
    conversion = convert_to_supported_excel(excel_path, normalized_path)
    normalization = SimpleNamespace(
        source_path=Path(excel_path),
        canonical_path=conversion["output"],
        source_format=(
            "multi-sheet test-case workbook"
            if conversion["sheets"] > 1 else "test-case workbook"
        ),
        case_count=conversion["cases"],
        step_count=conversion["steps"],
        sheet_count=conversion["sheets"],
    )
    reader, generator, ids = ExcelReader(), YAMLGenerator(), []
    for case in reader.group_cases(normalization.canonical_path):
        generation_steps = case["steps"] + case.get("automation_intents", [])
        mode, confidence, assumptions = "rules", None, []
        try:
            yaml_text, error = generator.generate_yaml(
                generation_steps, tags=["generated"], case_id=case["id"]
            ), None
        except Exception as exc:
            direct_error = str(exc)
            if use_ai:
                try:
                    design = _ai_rewrite({**case, "steps": generation_steps})
                    yaml_text = generator.generate_yaml(
                        design["test_steps"], tags=["generated", "ai-adapted"],
                        case_id=case["id"],
                    )
                    mode, error = "ai", None
                    confidence = float(design.get("confidence", 0))
                    assumptions = design.get("unresolved_assumptions", [])
                except Exception as ai_exc:
                    yaml_text = ""
                    error = f"Rules: {direct_error} | AI fallback: {ai_exc}"
            else:
                yaml_text, error = "", direct_error
        with connect() as db:
            cursor = db.execute(
                """INSERT INTO drafts(case_id,name,yaml,source_file,error,generation_mode,
                   ai_confidence,ai_assumptions) VALUES(?,?,?,?,?,?,?,?)""",
                (case["id"], case["name"], yaml_text, Path(excel_path).name, error,
                 mode, confidence, json.dumps(assumptions, ensure_ascii=False)),
            )
            ids.append(cursor.lastrowid)
    return ids, normalization


def approve_draft(draft_id, yaml_text, suite, reviewer):
    with connect() as db:
        draft = db.execute("SELECT * FROM drafts WHERE id=?", (draft_id,)).fetchone()
        if not draft or draft["status"] != "pending":
            raise ValueError("Draft is not pending")
        safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", draft["case_id"])
        filename = f"{safe_id}.yaml"
        (ROOT / "Scenarios" / filename).write_text(yaml_text, encoding="utf-8")
        suite_path = ROOT / "Suites" / f"{suite}.json"
        data = json.loads(suite_path.read_text(encoding="utf-8"))
        data["tests"] = [item for item in data.get("tests", []) if item.get("id") != draft["case_id"]]
        data["tests"].append({"id": draft["case_id"], "module": "AI Generated", "priority": "P2",
                              "name": draft["name"], "yaml": filename})
        suite_path.write_text(json.dumps(data, indent=4), encoding="utf-8")
        db.execute("UPDATE drafts SET yaml=?,status='approved',reviewed_at=CURRENT_TIMESTAMP,reviewed_by=? WHERE id=?",
                   (yaml_text, reviewer, draft_id))


def reject_draft(draft_id, reviewer):
    with connect() as db:
        db.execute("UPDATE drafts SET status='rejected',reviewed_at=CURRENT_TIMESTAMP,reviewed_by=? WHERE id=? AND status='pending'",
                   (reviewer, draft_id))
