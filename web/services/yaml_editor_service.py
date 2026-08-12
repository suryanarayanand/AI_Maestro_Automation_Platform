import re
import shutil
import json
from datetime import datetime
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ROOT / "Scenarios"
BACKUPS = ROOT / "Backups" / "YAML"
SUITES = ROOT / "Suites"
MAX_YAML_SIZE = 1024 * 1024


def list_scenarios(query=""):
    query = query.strip().lower()
    scenarios = []
    for path in sorted(SCENARIOS.rglob("*.yaml")):
        relative = path.relative_to(SCENARIOS).as_posix()
        if not query or query in relative.lower():
            scenarios.append({"path": relative, "name": path.name,
                              "folder": path.parent.relative_to(SCENARIOS).as_posix(),
                              "size": path.stat().st_size})
    return scenarios


def resolve_scenario(relative_path):
    normalized = PurePosixPath(relative_path)
    if normalized.is_absolute() or ".." in normalized.parts or normalized.suffix.lower() != ".yaml":
        raise ValueError("Invalid scenario path")
    candidate = (SCENARIOS / Path(*normalized.parts)).resolve()
    if not candidate.is_relative_to(SCENARIOS.resolve()) or not candidate.is_file():
        raise FileNotFoundError(relative_path)
    return candidate


def read_scenario(relative_path):
    return resolve_scenario(relative_path).read_text(encoding="utf-8")


def validate_maestro_yaml(content):
    if not content.strip():
        raise ValueError("YAML cannot be empty")
    if len(content.encode("utf-8")) > MAX_YAML_SIZE:
        raise ValueError("YAML exceeds the 1 MB editor limit")
    if "\x00" in content:
        raise ValueError("YAML contains a null character")
    if "\t" in content:
        raise ValueError("YAML indentation must use spaces, not tabs")
    lines = content.splitlines()
    separators = [index for index, line in enumerate(lines) if line.strip() == "---"]
    if not separators:
        raise ValueError("Maestro YAML must contain the '---' document separator")
    separator = separators[0]
    if not re.search(r"(?m)^appId\s*:\s*\S+", "\n".join(lines[:separator])):
        raise ValueError("Maestro YAML must define appId before '---'")
    if not any(re.match(r"^\s*-\s+[A-Za-z]", line) for line in lines[separator + 1:]):
        raise ValueError("Maestro YAML must contain at least one command after '---'")
    return True


def save_scenario(relative_path, content):
    path = resolve_scenario(relative_path)
    validate_maestro_yaml(content)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    relative = path.relative_to(SCENARIOS)
    backup = BACKUPS / relative.parent / f"{relative.stem}_{timestamp}.yaml"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup)
    path.write_text(content, encoding="utf-8")
    return backup.relative_to(ROOT).as_posix()


def delete_scenario(relative_path):
    """Delete an unreferenced scenario after preserving a recoverable backup."""
    path = resolve_scenario(relative_path)
    normalized = path.relative_to(SCENARIOS).as_posix().casefold()
    referenced_by = []
    for suite_path in SUITES.glob("*.json"):
        try:
            tests = json.loads(suite_path.read_text(encoding="utf-8")).get("tests", [])
        except (OSError, json.JSONDecodeError):
            continue
        if any(
            isinstance(test, dict)
            and str(test.get("yaml", "")).replace("\\", "/").casefold() == normalized
            for test in tests
        ):
            referenced_by.append(suite_path.stem)
    if referenced_by:
        suites = ", ".join(sorted(referenced_by, key=str.casefold))
        raise ValueError(f"Cannot delete YAML while it is referenced by suite(s): {suites}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    relative = path.relative_to(SCENARIOS)
    backup = BACKUPS / "Deleted" / relative.parent / f"{relative.stem}_{timestamp}.yaml"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup)
    path.unlink()
    return backup.relative_to(ROOT).as_posix()
