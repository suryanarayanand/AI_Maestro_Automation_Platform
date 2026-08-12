import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SYSTEM_PREFIXES = ("com.android.systemui", "android:")
SYSTEM_KEYWORDS = (
    "status_bar", "battery", "wifi", "mobile_signal", "notification",
    "clock", "system_icon", "signal",
)


def main():
    parser = argparse.ArgumentParser(description="Remove Android system elements from a locator repository.")
    parser.add_argument("--input", type=Path, default=ROOT / "LocatorRepository" / "locator_repository.json")
    parser.add_argument("--output", type=Path, default=ROOT / "LocatorRepository" / "smart_locator_repository.json")
    args = parser.parse_args()

    locators = json.loads(args.input.read_text(encoding="utf-8"))
    cleaned = []
    seen = set()
    for item in locators:
        locator = item.get("locator", {})
        value = str(locator.get("value", "")).strip()
        key = (locator.get("type"), value)
        value_lower = value.lower()
        if not value or key in seen:
            continue
        if value.startswith(SYSTEM_PREFIXES) or any(word in value_lower for word in SYSTEM_KEYWORDS):
            continue
        seen.add(key)
        cleaned.append(item)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(cleaned, indent=4, ensure_ascii=False), encoding="utf-8")
    print(f"Original: {len(locators)}")
    print(f"Cleaned: {len(cleaned)}")
    print(f"Saved to: {args.output}")


if __name__ == "__main__":
    main()
