import json
import sqlite3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
suite_path = root / "Suites" / "user_anonymous.json"
suite = json.loads(suite_path.read_text(encoding="utf-8"))
suite["tests"] = [
    test for test in suite.get("tests", [])
    if not str(test.get("id", "")).startswith(("ANON_PREM_", "ANON_EBOOK_"))
]

db = sqlite3.connect(root / "portal.db")
db.row_factory = sqlite3.Row
rows = db.execute(
    "SELECT case_id,name,user_state FROM drafts WHERE status='approved' "
    "AND source_file IN (?,?) ORDER BY case_id",
    ("Anonymous_Premium_Approved_Test_Cases.xlsx", "Anonymous_EBooks_Approved_Test_Cases.xlsx"),
).fetchall()
db.close()

seen = set()
for row in rows:
    case_id = row["case_id"]
    if case_id in seen:
        continue
    seen.add(case_id)
    module = "Premium" if case_id.startswith("ANON_PREM_") else "eBooks"
    suite["tests"].append({
        "id": case_id, "module": module, "section": module,
        "user_state": row["user_state"], "priority": "P2",
        "name": row["name"], "yaml": f"{case_id}.yaml",
    })

suite["modules"] = [
    module for module in suite.get("modules", [])
    if str(module).casefold() not in {"home", "premium", "login", "trending", "ebooks", "ebook", "games"}
]
suite_path.write_text(json.dumps(suite, indent=4, ensure_ascii=False), encoding="utf-8")
print("suite cases", len(suite["tests"]), "approved module cases", len(seen))
