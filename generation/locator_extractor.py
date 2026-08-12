import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HIERARCHIES = ROOT / "Hierarchies"
DEFAULT_OUTPUT = ROOT / "LocatorRepository" / "locator_repository.json"
DEFAULT_EXISTING = ROOT / "LocatorRepository" / "smart_locator_repository.json"


def load_json(path):
    for encoding in ("utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be"):
        try:
            return json.loads(path.read_text(encoding=encoding))
        except (UnicodeError, json.JSONDecodeError):
            continue
    raise ValueError(f"Unable to read hierarchy JSON: {path}")


def best_locator(attributes):
    for key, locator_type, priority in (
        ("resource-id", "id", 1),
        ("accessibilityText", "accessibilityText", 2),
        ("text", "text", 3),
    ):
        value = str(attributes.get(key, "")).strip()
        if value:
            return {"type": locator_type, "value": value, "priority": priority}
    return None


def extract_tree(node, source, output):
    attributes = node.get("attributes", {})
    locator = best_locator(attributes)
    if locator:
        output.append({
            "name": (
                str(attributes.get("resource-id", "")).strip()
                or str(attributes.get("accessibilityText", "")).strip()
                or str(attributes.get("text", "")).strip()
            ),
            "locator": locator,
            "class": attributes.get("class", ""),
            "clickable": attributes.get("clickable", False),
            "scrollable": attributes.get("scrollable", False),
            "enabled": attributes.get("enabled", True),
            "bounds": attributes.get("bounds", ""),
            "sources": [source],
        })
    for child in node.get("children", []):
        extract_tree(child, source, output)


def merge_locators(locators):
    merged = {}
    for item in locators:
        locator = item.get("locator", {})
        key = (locator.get("type"), locator.get("value"))
        if not all(key):
            continue
        if key not in merged:
            merged[key] = item
            merged[key]["sources"] = list(item.get("sources", []))
        else:
            sources = merged[key].setdefault("sources", [])
            for source in item.get("sources", []):
                if source not in sources:
                    sources.append(source)
            if str(item.get("clickable", "")).lower() == "true":
                merged[key]["clickable"] = item["clickable"]
    return sorted(
        merged.values(),
        key=lambda item: (item["locator"].get("priority", 99), item["name"].lower()),
    )


def main():
    parser = argparse.ArgumentParser(description="Merge Maestro hierarchy JSON files into the locator repository.")
    parser.add_argument("inputs", nargs="*", type=Path, help="Hierarchy JSON files; defaults to Hierarchies/*.json")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--no-existing", action="store_true", help="Do not merge the existing smart repository")
    args = parser.parse_args()

    hierarchy_files = args.inputs or sorted(DEFAULT_HIERARCHIES.glob("*.json"))
    if not hierarchy_files:
        raise SystemExit("No hierarchy JSON files found")

    locators = []
    if not args.no_existing and DEFAULT_EXISTING.is_file():
        existing = load_json(DEFAULT_EXISTING)
        for item in existing:
            item = dict(item)
            item.setdefault("sources", ["existing_repository"])
            locators.append(item)

    for path in hierarchy_files:
        hierarchy = load_json(path)
        extract_tree(hierarchy, path.name, locators)

    merged = merge_locators(locators)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(merged, indent=4, ensure_ascii=False), encoding="utf-8")
    print(f"Hierarchy files: {len(hierarchy_files)}")
    print(f"Merged locators: {len(merged)}")
    print(f"Saved to: {args.output}")


if __name__ == "__main__":
    main()
