"""Persistent, repository-grounded memory of the mobile application UI."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from web.portal_db import connect


ROOT = Path(__file__).resolve().parents[2]
HIERARCHIES = ROOT / "Hierarchies"
VALIDATED_LOCATORS = ROOT / "LocatorRepository" / "validated_locator_repository.json"
TIMESTAMP_SUFFIX = re.compile(r"_\d{8}_\d{6}$")


def safe_name(value):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", str(value)).strip("_") or "screen"


def load_json_file(path):
    path = Path(path)
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16"):
        try:
            return json.loads(raw.decode(encoding))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    raise ValueError(f"Unsupported or invalid hierarchy JSON: {path}")


def screen_name_from_path(path):
    return TIMESTAMP_SUFFIX.sub("", Path(path).stem)


def walk_nodes(node):
    if not isinstance(node, dict):
        return
    yield node
    for child in node.get("children", []):
        yield from walk_nodes(child)


def _clean_resource_id(value):
    value = str(value or "").strip()
    if value.startswith(("android:", "com.android.systemui:")):
        return ""
    if ":id/" in value:
        value = value.split(":id/", 1)[1]
    return value


def extract_elements(hierarchy):
    """Extract stable selector candidates from a Maestro hierarchy."""
    found = {}
    for node in walk_nodes(hierarchy):
        attributes = node.get("attributes") or {}
        resource_id = _clean_resource_id(attributes.get("resource-id"))
        accessibility = str(attributes.get("accessibilityText") or "").strip()
        text = str(attributes.get("text") or "").strip()
        candidates = []
        if resource_id:
            candidates.append(("id", resource_id, 0.90))
        if accessibility:
            candidates.append(("text", accessibility, 0.75))
        if text:
            candidates.append(("text", text, 0.65))
        for locator_type, locator_value, confidence in candidates:
            key = (locator_type, locator_value)
            found.setdefault(key, {
                "name": resource_id or accessibility or text,
                "locator_type": locator_type,
                "locator_value": locator_value,
                "class_name": attributes.get("class", ""),
                "clickable": str(attributes.get("clickable", "false")).lower() == "true",
                "enabled": str(attributes.get("enabled", "true")).lower() == "true",
                "bounds": attributes.get("bounds", ""),
                "source": "hierarchy",
                "confidence": confidence,
            })
    return list(found.values())


def hierarchy_fingerprint(elements):
    stable = sorted(
        f"{item['locator_type']}:{item['locator_value']}"
        for item in elements if item["confidence"] >= 0.75
    )
    return hashlib.sha256("\n".join(stable).encode("utf-8")).hexdigest()


def _upsert_screen(db, name, fingerprint, hierarchy_file=None, element_count=0):
    db.execute(
        """INSERT INTO app_memory_screens(name,fingerprint,hierarchy_file,element_count)
           VALUES(?,?,?,?) ON CONFLICT(name) DO UPDATE SET
           fingerprint=CASE WHEN excluded.hierarchy_file IS NULL
                       THEN app_memory_screens.fingerprint ELSE excluded.fingerprint END,
           hierarchy_file=COALESCE(excluded.hierarchy_file,app_memory_screens.hierarchy_file),
           element_count=MAX(app_memory_screens.element_count,excluded.element_count),
           last_seen_at=CURRENT_TIMESTAMP""",
        (name, fingerprint, hierarchy_file, element_count),
    )
    return db.execute("SELECT id FROM app_memory_screens WHERE name=?", (name,)).fetchone()[0]


def import_hierarchy(path):
    path = Path(path)
    hierarchy = load_json_file(path)
    elements = extract_elements(hierarchy)
    name = screen_name_from_path(path)
    with connect() as db:
        screen_id = _upsert_screen(db, name, hierarchy_fingerprint(elements), str(path), len(elements))
        for item in elements:
            db.execute(
                """INSERT INTO app_memory_elements(
                   screen_id,name,locator_type,locator_value,class_name,clickable,enabled,
                   bounds,source,confidence) VALUES(?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(screen_id,locator_type,locator_value) DO UPDATE SET
                   name=excluded.name,class_name=excluded.class_name,clickable=excluded.clickable,
                   enabled=excluded.enabled,bounds=excluded.bounds,
                   confidence=MAX(app_memory_elements.confidence,excluded.confidence)""",
                (screen_id, item["name"], item["locator_type"], item["locator_value"],
                 item["class_name"], item["clickable"], item["enabled"], item["bounds"],
                 item["source"], item["confidence"]),
            )
    return name, len(elements)


def import_validated_locators():
    records = json.loads(VALIDATED_LOCATORS.read_text(encoding="utf-8")) if VALIDATED_LOCATORS.is_file() else []
    with connect() as db:
        for item in records:
            screen_name = str(item.get("screen") or "unknown").strip()
            screen_id = _upsert_screen(db, screen_name, "validated-only")
            locator = item.get("locator") or {}
            if not locator.get("type") or not locator.get("value"):
                continue
            db.execute(
                """INSERT INTO app_memory_elements(
                   screen_id,name,locator_type,locator_value,class_name,clickable,enabled,
                   bounds,source,confidence) VALUES(?,?,?,?,?,?,?,?,?,1.0)
                   ON CONFLICT(screen_id,locator_type,locator_value) DO UPDATE SET
                   source='validated',confidence=1.0""",
                (screen_id, item.get("name") or locator["value"], locator["type"],
                 locator["value"], item.get("class", ""),
                 str(item.get("clickable", "false")).lower() == "true",
                 str(item.get("enabled", "true")).lower() == "true",
                 item.get("bounds", ""), "validated"),
            )
    return len(records)


def rebuild_memory():
    imported = [import_hierarchy(path) for path in sorted(HIERARCHIES.glob("*.json"))]
    validated = import_validated_locators()
    flows = index_yaml_flows()
    executions = backfill_execution_learning()
    return {"hierarchies": len(imported), "validated_locators": validated,
            "flows": flows, "executions": executions}


def backfill_execution_learning():
    """Turn historical results into positive/negative evidence without promoting failures."""
    from web.services.adaptive_test_agent import AdaptiveTestAgent
    from web.services.yaml_editor_service import account_tag

    with connect() as db:
        rows = db.execute(
            """SELECT r.*,j.suite FROM job_results r
               JOIN jobs j ON j.id=r.job_id ORDER BY r.id"""
        ).fetchall()
    suite_cache = {}
    learned = 0
    for row in rows:
        if row["suite"] not in suite_cache:
            path = ROOT / "Suites" / f"{row['suite']}.json"
            try:
                suite_cache[row["suite"]] = json.loads(path.read_text(encoding="utf-8")).get("tests", [])
            except (OSError, json.JSONDecodeError):
                suite_cache[row["suite"]] = []
        test = next((item for item in suite_cache[row["suite"]]
                     if item.get("id") == row["case_id"]), {})
        scenario = ROOT / "Scenarios" / str(test.get("yaml", ""))
        yaml_text = scenario.read_text(encoding="utf-8-sig", errors="replace") if scenario.is_file() else ""
        state = account_tag(test.get("yaml", ""), yaml_text).upper()
        AdaptiveTestAgent.learn_from_execution(
            row["case_id"], row["status"], row["stdout"], row["stderr"],
            source=f"job:{row['job_id']}:case:{row['case_id']}", yaml_text=yaml_text,
            name=row["name"] or row["case_id"], user_state=state,
        )
        learned += 1
    return learned


def index_yaml_flows():
    """Remember ordered command demonstrations from every scenario/common YAML."""
    from web.services.yaml_editor_service import extract_tags

    paths = sorted((ROOT / "Scenarios").rglob("*.yaml")) + sorted((ROOT / "Common").rglob("*.yaml"))
    result_counts = {}
    with connect() as db:
        results = db.execute(
            "SELECT case_id,status,COUNT(*) count FROM job_results GROUP BY case_id,status"
        ).fetchall()
    case_counts = {}
    for row in results:
        bucket = case_counts.setdefault(row["case_id"], {"pass": 0, "fail": 0})
        if row["status"] == "PASS":
            bucket["pass"] += row["count"]
        elif row["status"] in {"FAIL", "NEEDS_REVIEW", "CANCELLED"}:
            bucket["fail"] += row["count"]
    for suite_path in (ROOT / "Suites").glob("*.json"):
        try:
            tests = json.loads(suite_path.read_text(encoding="utf-8")).get("tests", [])
        except (OSError, json.JSONDecodeError):
            continue
        for test in tests:
            relative = f"Scenarios/{str(test.get('yaml', '')).replace(chr(92), '/')}"
            counts = case_counts.get(test.get("id"), {})
            target = result_counts.setdefault(relative.casefold(), {"pass": 0, "fail": 0})
            target["pass"] += counts.get("pass", 0)
            target["fail"] += counts.get("fail", 0)
    with connect() as db:
        for path in paths:
            content = path.read_text(encoding="utf-8-sig", errors="replace")
            commands = re.findall(r"^\s*-\s+([A-Za-z][A-Za-z0-9]*)(?::|\s*$)", content, re.MULTILINE)
            relative = path.relative_to(ROOT).as_posix()
            counts = result_counts.get(relative.casefold(), {"pass": 0, "fail": 0})
            search_text = " ".join((relative, *re.findall(r"(?m)^\s*#\s*(.+)$", content)))[:8000]
            db.execute(
                """INSERT INTO app_memory_flows(
                   path,flow_type,content_hash,command_sequence,search_text,tags,pass_count,fail_count)
                   VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(path) DO UPDATE SET
                   flow_type=excluded.flow_type,content_hash=excluded.content_hash,
                   command_sequence=excluded.command_sequence,search_text=excluded.search_text,
                   tags=excluded.tags,pass_count=excluded.pass_count,fail_count=excluded.fail_count,
                   last_indexed_at=CURRENT_TIMESTAMP""",
                (relative, relative.split("/", 1)[0].lower(),
                 hashlib.sha256(content.encode("utf-8")).hexdigest(), json.dumps(commands),
                 search_text, json.dumps(extract_tags(content)), counts["pass"], counts["fail"]),
            )
    return len(paths)


def capture_current_screen(name, device=None):
    """Read the current hierarchy without interacting with the application."""
    executable = shutil.which("maestro.bat" if os.name == "nt" else "maestro")
    if not executable:
        raise RuntimeError("Maestro executable was not found on PATH.")
    command = [executable]
    if device:
        command.extend(["--udid", device])
    command.extend(["hierarchy", "--no-ansi", "--no-reinstall-driver"])
    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "Hierarchy capture failed.")
    start, end = result.stdout.find("{"), result.stdout.rfind("}")
    if start < 0 or end < start:
        raise RuntimeError("Maestro hierarchy output did not contain JSON.")
    hierarchy = json.loads(result.stdout[start:end + 1])
    output = HIERARCHIES / f"{safe_name(name)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output.write_text(json.dumps(hierarchy, indent=2, ensure_ascii=False), encoding="utf-8")
    screen, elements = import_hierarchy(output)
    return {"screen": screen, "elements": elements, "path": output}


def memory_summary():
    with connect() as db:
        totals = db.execute(
            """SELECT (SELECT COUNT(*) FROM app_memory_screens) screens,
                      (SELECT COUNT(*) FROM app_memory_elements) elements,
                      (SELECT COUNT(*) FROM app_memory_elements WHERE confidence=1.0) validated,
                      (SELECT COUNT(*) FROM app_memory_transitions) transitions,
                      (SELECT COUNT(*) FROM app_memory_learning WHERE status='pending') pending_learning,
                      (SELECT COUNT(*) FROM app_memory_flows) flows"""
        ).fetchone()
        screens = db.execute(
            """SELECT s.*,COUNT(e.id) remembered_elements,
               SUM(CASE WHEN e.confidence=1.0 THEN 1 ELSE 0 END) validated_elements
               FROM app_memory_screens s LEFT JOIN app_memory_elements e ON e.screen_id=s.id
               GROUP BY s.id ORDER BY s.last_seen_at DESC,s.name"""
        ).fetchall()
        learning = db.execute(
            """SELECT * FROM app_memory_learning WHERE status='pending'
               ORDER BY id DESC LIMIT 50"""
        ).fetchall()
    return dict(totals), screens, learning
