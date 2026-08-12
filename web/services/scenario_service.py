from pathlib import Path
import json
import os

from web.portal_db import connect

ROOT = Path(__file__).resolve().parents[2]
SUITE_FOLDER = ROOT / "Suites"
SCENARIO_FOLDER = ROOT / "Scenarios"


def get_all_suites():
    suites = []

    with connect() as db:
        completed_jobs = db.execute(
            "SELECT id,suite,status,finished_at FROM jobs "
            "WHERE status IN ('passed','failed','cancelled') ORDER BY id DESC"
        ).fetchall()
    latest_by_suite = {}
    for job in completed_jobs:
        latest_by_suite.setdefault(str(job["suite"]).casefold(), dict(job))

    for file in sorted(SUITE_FOLDER.glob("*.json"), key=lambda path: path.stem.lower()):

        try:

            with open(file, "r", encoding="utf-8") as f:

                data = json.load(f)

            test_count = len(data.get("tests", []))

        except Exception:

            test_count = 0

        suites.append({
            "name": file.stem.title(),
            "key": file.stem,
            "file": file.name,
            "count": test_count,
            "last_result": latest_by_suite.get(file.stem.casefold()),
        })

    return suites


def _suite_path(suite_name):
    """Resolve an existing suite by stem without accepting filesystem paths."""
    requested = str(suite_name).casefold()
    for path in SUITE_FOLDER.glob("*.json"):
        if path.stem.casefold() == requested:
            return path
    return None


def _read_suite(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("tests", []), list):
        raise ValueError("Suite JSON must contain a tests list.")
    return data


def _scenario_paths():
    return sorted(
        (path.relative_to(SCENARIO_FOLDER).as_posix() for path in SCENARIO_FOLDER.rglob("*.yaml")),
        key=str.casefold,
    )


def _default_test(yaml_path):
    stem = Path(yaml_path).stem
    case_id = stem.split("_", 2)
    if len(case_id) >= 2 and case_id[0].upper() in {"SC", "GEN", "TH", "LOC"}:
        test_id = f"{case_id[0]}_{case_id[1]}"
    else:
        test_id = stem
    return {
        "id": test_id,
        "module": "Unassigned",
        "priority": "P2",
        "name": stem.replace("_", " "),
        "yaml": yaml_path,
    }


def get_suite_editor(suite_name):
    path = _suite_path(suite_name)
    if path is None:
        return None
    data = _read_suite(path)
    tests = [test for test in data.get("tests", []) if isinstance(test, dict) and test.get("yaml")]
    selected_paths = [str(test["yaml"]).replace("\\", "/") for test in tests]
    selected_set = {item.casefold() for item in selected_paths}
    scenarios = _scenario_paths()
    return {
        "key": path.stem,
        "name": data.get("suite") or path.stem,
        "tests": tests,
        "available": [item for item in scenarios if item.casefold() not in selected_set],
    }


def save_suite_tests(suite_name, ordered_yaml_paths):
    path = _suite_path(suite_name)
    if path is None:
        raise ValueError("Suite not found.")

    valid_paths = {item.casefold(): item for item in _scenario_paths()}
    normalized = []
    seen = set()
    for submitted in ordered_yaml_paths:
        key = str(submitted).replace("\\", "/").casefold()
        if key not in valid_paths:
            raise ValueError(f"Unknown scenario: {submitted}")
        if key in seen:
            raise ValueError(f"Duplicate scenario: {submitted}")
        seen.add(key)
        normalized.append(valid_paths[key])

    data = _read_suite(path)
    metadata = {}
    for suite_path in SUITE_FOLDER.glob("*.json"):
        try:
            suite_data = _read_suite(suite_path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        for test in suite_data.get("tests", []):
            if isinstance(test, dict) and test.get("yaml"):
                metadata.setdefault(str(test["yaml"]).replace("\\", "/").casefold(), test)

    current = {
        str(test["yaml"]).replace("\\", "/").casefold(): test
        for test in data.get("tests", [])
        if isinstance(test, dict) and test.get("yaml")
    }
    new_tests = []
    for yaml_path in normalized:
        source = current.get(yaml_path.casefold()) or metadata.get(yaml_path.casefold())
        test = dict(source) if source else _default_test(yaml_path)
        test["yaml"] = yaml_path
        new_tests.append(test)
    data["tests"] = new_tests

    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return len(new_tests)


def delete_suite(suite_name):
    """Delete one suite definition without deleting any scenario YAML files."""
    path = _suite_path(suite_name)
    if path is None:
        raise ValueError("Suite not found.")
    path.unlink()
    return path.stem
