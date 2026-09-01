"""Extract conservative locator candidates from Android/Kotlin source code."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from web.portal_db import connect


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "LocatorRepository" / "source_locator_repository.json"


PATTERNS = (
    ("id", "testTag", re.compile(r"\.testTag\(\s*\"([^\"]+)\"\s*\)"), 0.95),
    ("id", "automationTag", re.compile(r"\.automationTag\(\s*\"([^\"]+)\"\s*\)"), 0.95),
    ("text", "contentDescription", re.compile(
        r"contentDescription\s*=\s*\"([^\"]+)\""
    ), 0.85),
    ("id", "xml-id", re.compile(
        r"android:id\s*=\s*\"@\+?id/([^\"]+)\""
    ), 0.95),
    ("text", "compose-text", re.compile(
        r"\bText\(\s*(?:text\s*=\s*)?\"([^\"]{2,80})\""
    ), 0.55),
)

TAG_CONSTANT = re.compile(r"\bconst\s+val\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\"([^\"]+)\"")
TAG_REFERENCE = re.compile(
    r"\.(?:testTag|automationTag)\(\s*AutomationTestTags\.([A-Za-z_][A-Za-z0-9_]*)\s*\)"
)


def _name(value):
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower() or "locator"


def extract_source_locators(source_root):
    source_root = Path(source_root).resolve()
    if not source_root.is_dir():
        raise ValueError("Android/Kotlin source directory does not exist.")
    records = {}
    files = [*source_root.rglob("*.kt"), *source_root.rglob("*.xml")]
    tag_constants = {}
    for path in files:
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for match in TAG_CONSTANT.finditer(content):
            symbol, value = match.group(1), match.group(2)
            tag_constants[symbol] = value
            if path.name == "AutomationTestTags.kt":
                relative = path.relative_to(source_root).as_posix()
                records[("id", value.casefold())] = {
                    "name": value,
                    "locator": {"type": "id", "value": value, "priority": 1},
                    "status": "candidate", "confidence": 0.95,
                    "source_type": "application_source",
                    "mechanisms": ["automationTag-catalog"],
                    "sources": [f"{relative}:{content.count(chr(10), 0, match.start()) + 1}"],
                    "notes": "Source evidence only; validate against the installed build before execution.",
                }
    for path in files:
        relative_parts = {part.casefold() for part in path.relative_to(source_root).parts}
        if relative_parts.intersection({"test", "androidtest", "commontest", "iostest"}):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        relative = path.relative_to(source_root).as_posix()
        for locator_type, mechanism, pattern, confidence in PATTERNS:
            for match in pattern.finditer(content):
                value = match.group(1).strip()
                if (not value or value.casefold() in {"null", "true", "false"}
                        or (mechanism == "compose-text" and not re.search(r"[A-Za-z]", value))):
                    continue
                key = (locator_type, value.casefold())
                record = records.setdefault(key, {
                    "name": value if locator_type == "id" else _name(value),
                    "locator": {"type": locator_type, "value": value,
                                "priority": 1 if locator_type == "id" else 3},
                    "status": "candidate",
                    "confidence": confidence,
                    "source_type": "application_source",
                    "mechanisms": [], "sources": [],
                    "notes": "Source evidence only; validate against the installed build before execution.",
                })
                record["confidence"] = max(record["confidence"], confidence)
                if mechanism not in record["mechanisms"]:
                    record["mechanisms"].append(mechanism)
                location = f"{relative}:{content.count(chr(10), 0, match.start()) + 1}"
                if location not in record["sources"]:
                    record["sources"].append(location)
        for match in TAG_REFERENCE.finditer(content):
            value = tag_constants.get(match.group(1), "").strip()
            if not value:
                continue
            key = ("id", value.casefold())
            record = records.setdefault(key, {
                "name": value,
                "locator": {"type": "id", "value": value, "priority": 1},
                "status": "candidate",
                "confidence": 0.95,
                "source_type": "application_source",
                "mechanisms": [], "sources": [],
                "notes": "Source evidence only; validate against the installed build before execution.",
            })
            if "automationTag-constant" not in record["mechanisms"]:
                record["mechanisms"].append("automationTag-constant")
            location = f"{relative}:{content.count(chr(10), 0, match.start()) + 1}"
            if location not in record["sources"]:
                record["sources"].append(location)
    return sorted(records.values(), key=lambda item: (
        item["locator"]["type"], item["locator"]["value"].casefold()
    ))


def import_source_locators(source_root, output=OUTPUT):
    records = extract_source_locators(source_root)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    os.replace(temporary, output)
    with connect() as db:
        db.execute(
            """INSERT INTO app_memory_screens(name,fingerprint,hierarchy_file,element_count)
               VALUES('application_source','source-code',?,?)
               ON CONFLICT(name) DO UPDATE SET hierarchy_file=excluded.hierarchy_file,
               element_count=excluded.element_count,last_seen_at=CURRENT_TIMESTAMP""",
            (str(Path(source_root).resolve()), len(records)),
        )
        screen_id = db.execute(
            "SELECT id FROM app_memory_screens WHERE name='application_source'"
        ).fetchone()[0]
        db.execute(
            "DELETE FROM app_memory_elements WHERE screen_id=? AND source='application_source'",
            (screen_id,),
        )
        for item in records:
            locator = item["locator"]
            db.execute(
                """INSERT INTO app_memory_elements(
                   screen_id,name,locator_type,locator_value,class_name,clickable,enabled,
                   bounds,source,confidence) VALUES(?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(screen_id,locator_type,locator_value) DO UPDATE SET
                   name=excluded.name,source=excluded.source,confidence=excluded.confidence""",
                (screen_id, item["name"], locator["type"], locator["value"], "", False,
                 True, "", "application_source", item["confidence"]),
            )
    return {"source_root": str(Path(source_root).resolve()), "count": len(records),
            "strong": sum(item["confidence"] >= 0.85 for item in records),
            "output": str(output)}
