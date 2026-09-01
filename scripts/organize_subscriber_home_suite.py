import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
updated = []
for path in (ROOT / "Suites").glob("*.json"):
    data = json.loads(path.read_text(encoding="utf-8"))
    changed = False
    for test in data.get("tests", []):
        if str(test.get("id", "")).upper().startswith("SUB_HOME_"):
            test["module"] = "Home"
            test["section"] = "Home"
            test["user_state"] = "SUBSCRIBER"
            changed = True
    if path.stem == "user_subscriber":
        subscriber_home = [
            test for test in data.get("tests", [])
            if str(test.get("id", "")).upper().startswith("SUB_HOME_")
        ]
        remaining = [test for test in data.get("tests", []) if test not in subscriber_home]
        subscriber_home.sort(key=lambda test: str(test.get("id", "")))
        data["tests"] = subscriber_home + remaining
        changed = True
    if changed:
        path.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")
        updated.append(path.name)
print("Updated:", ", ".join(updated))
