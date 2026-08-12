import argparse
import csv
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CANDIDATES = ROOT / "LocatorRepository" / "smart_locator_repository.json"
VALIDATED = ROOT / "LocatorRepository" / "validated_locator_repository.json"
CSV_EXPORT = ROOT / "LocatorRepository" / "validated_locator_repository.csv"


def load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []


def save(records):
    VALIDATED.write_text(json.dumps(records, indent=4, ensure_ascii=False), encoding="utf-8")


def export_csv(records):
    with CSV_EXPORT.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "name", "screen", "type", "value", "priority", "status",
            "validated_at", "source", "notes",
        ])
        writer.writeheader()
        for item in records:
            locator = item.get("locator", {})
            writer.writerow({
                "name": item.get("name", ""),
                "screen": item.get("screen", ""),
                "type": locator.get("type", ""),
                "value": locator.get("value", ""),
                "priority": locator.get("priority", ""),
                "status": item.get("status", "validated"),
                "validated_at": item.get("validated_at", ""),
                "source": item.get("source", ""),
                "notes": item.get("notes", ""),
            })


def promote(name, screen, notes):
    candidates = load(CANDIDATES)
    matches = [
        item for item in candidates
        if item.get("name", "").lower() == name.lower()
        or item.get("locator", {}).get("value", "").lower() == name.lower()
    ]
    if not matches:
        raise SystemExit(f"Candidate locator not found: {name}")
    if len(matches) > 1:
        exact = [item for item in matches if item.get("name", "").lower() == name.lower()]
        matches = exact or matches
    candidate = dict(matches[0])
    candidate.update({
        "screen": screen,
        "status": "validated",
        "validated_at": datetime.now().isoformat(timespec="seconds"),
        "source": ", ".join(candidate.get("sources", [])),
        "notes": notes,
    })
    candidate.pop("sources", None)

    records = load(VALIDATED)
    key = (candidate["screen"].lower(), candidate["name"].lower())
    records = [
        item for item in records
        if (item.get("screen", "").lower(), item.get("name", "").lower()) != key
    ]
    records.append(candidate)
    records.sort(key=lambda item: (item.get("screen", ""), item.get("name", "")))
    save(records)
    export_csv(records)
    print(f"Validated: {candidate['screen']} / {candidate['name']}")


def main():
    parser = argparse.ArgumentParser(description="Manage reusable validated Maestro locators.")
    subcommands = parser.add_subparsers(dest="command", required=True)
    promote_parser = subcommands.add_parser("promote", help="Promote an exercised candidate locator")
    promote_parser.add_argument("name")
    promote_parser.add_argument("--screen", required=True)
    promote_parser.add_argument("--notes", default="Verified on connected device")
    subcommands.add_parser("export", help="Regenerate the CSV export")
    subcommands.add_parser("list", help="List validated locators")
    args = parser.parse_args()

    if args.command == "promote":
        promote(args.name, args.screen, args.notes)
    else:
        records = load(VALIDATED)
        if args.command == "export":
            export_csv(records)
            print(CSV_EXPORT)
        else:
            for item in records:
                locator = item.get("locator", {})
                print(f"{item.get('screen')} | {item.get('name')} | {locator.get('type')}={locator.get('value')}")
            print(f"Total: {len(records)}")


if __name__ == "__main__":
    main()
