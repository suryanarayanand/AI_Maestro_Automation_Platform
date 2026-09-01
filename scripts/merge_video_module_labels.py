import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
changed = 0
for path in (ROOT / "Suites").glob("*.json"):
    original = path.read_text(encoding="utf-8")
    try:
        data = json.loads(original)
    except json.JSONDecodeError:
        continue

    def normalize(value):
        if isinstance(value, dict):
            return {key: normalize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [normalize(item) for item in value]
        if value == "Videos Quick Access":
            return "Videos"
        return value

    normalized = normalize(data)
    rendered = json.dumps(normalized, indent=4, ensure_ascii=False) + "\n"
    if rendered != original:
        try:
            path.write_text(rendered, encoding="utf-8")
            changed += 1
        except PermissionError:
            # Historical/locked suites are execution evidence, not active metadata.
            continue

print(f"Normalized Videos module labels in {changed} suite files")
