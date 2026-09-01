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
            "WHERE status IN ('passed','failed','needs_review','cancelled') ORDER BY id DESC"
        ).fetchall()
    latest_by_suite = {}
    for job in completed_jobs:
        latest_by_suite.setdefault(str(job["suite"]).casefold(), dict(job))

    for file in sorted(SUITE_FOLDER.glob("*.json"), key=lambda path: path.stem.lower()):

        try:

            with open(file, "r", encoding="utf-8") as f:

                data = json.load(f)

            tests = [test for test in data.get("tests", []) if isinstance(test, dict)]
            test_count = len(tests)
            profile_counts = {}
            module_counts = {}
            section_counts = {}
            for test in tests:
                profile = str(test.get("user_state") or "UNSPECIFIED").strip().upper()
                module = str(test.get("module") or "Unassigned").strip()
                section = str(test.get("section") or "Unassigned").strip()
                profile_counts[profile] = profile_counts.get(profile, 0) + 1
                module_counts[module] = module_counts.get(module, 0) + 1
                section_counts[section] = section_counts.get(section, 0) + 1

        except Exception:

            test_count = 0
            data = {}
            profile_counts = {}
            module_counts = {}
            section_counts = {}

        suites.append({
            "name": data.get("suite") or file.stem.replace("_", " ").title(),
            "key": file.stem,
            "file": file.name,
            "count": test_count,
            "profiles": sorted(profile_counts),
            "profile_counts": profile_counts,
            "modules": sorted(module_counts, key=str.casefold),
            "module_counts": module_counts,
            "sections": sorted(section_counts, key=str.casefold),
            "section_counts": section_counts,
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


def validate_suite_definition(data):
    """Fail fast on ambiguous identities or missing scenario files."""
    errors, seen_ids, seen_yaml = [], set(), set()
    for position, test in enumerate(data.get("tests", []), start=1):
        if not isinstance(test, dict):
            errors.append(f"Test {position} is not an object")
            continue
        case_id = str(test.get("id") or "").strip()
        yaml_path = str(test.get("yaml") or "").replace("\\", "/").strip()
        if not case_id:
            errors.append(f"Test {position} has no case ID")
        elif case_id.casefold() in seen_ids:
            errors.append(f"Duplicate case ID: {case_id}")
        seen_ids.add(case_id.casefold())
        if not yaml_path:
            errors.append(f"{case_id or position} has no YAML path")
        elif yaml_path.casefold() in seen_yaml:
            errors.append(f"Duplicate scenario path: {yaml_path}")
        elif not (SCENARIO_FOLDER / yaml_path).is_file():
            errors.append(f"Scenario file not found: {yaml_path}")
        seen_yaml.add(yaml_path.casefold())
    return errors


def _scenario_paths():
    return sorted(
        (path.relative_to(SCENARIO_FOLDER).as_posix() for path in SCENARIO_FOLDER.rglob("*.yaml")),
        key=str.casefold,
    )


def _default_test(yaml_path):
    stem = Path(yaml_path).stem
    return {
        # Full stems avoid collapsing SC_27_SUDOKU, SC_27_NEWS_QUIZ, etc.
        "id": stem,
        "module": "Unassigned",
        "priority": "P2",
        "name": stem.replace("_", " "),
        "yaml": yaml_path,
    }


def _display_module(test):
    """Map legacy metadata into tester-facing module navigation."""
    explicit = str(test.get("module") or "").strip()
    if explicit and explicit.casefold() not in {"unassigned", "scenarios", "other"}:
        return explicit
    evidence = " ".join(str(test.get(key) or "") for key in (
        "module", "section", "name", "id", "yaml"
    )).casefold()
    if any(token in evidence for token in ("login", "sign in", "signin", "account", "auth")):
        return "Login"
    if any(token in evidence for token in (
        "premium", "subscribe", "subscription", "briefing", "specials"
    )):
        return "Premium"
    if "trending" in evidence:
        return "Trending"
    if any(token in evidence for token in ("ebook", "e-book", "ebooks")):
        return "eBooks"
    if any(token in evidence for token in ("game", "games")):
        return "Games"
    if any(token in evidence for token in ("home", "homepage", "article")):
        return "Home"
    return "Other"


def get_suite_editor(suite_name):
    path = _suite_path(suite_name)
    if path is None:
        return None
    data = _read_suite(path)
    tests = [dict(test) for test in data.get("tests", []) if isinstance(test, dict) and test.get("yaml")]
    default_modules = ["Home", "Premium", "Login", "Trending", "eBooks", "Games"]
    custom_modules = [
        str(module).strip() for module in data.get("modules", [])
        if str(module).strip() and str(module).strip() not in default_modules
    ]
    explicit_modules = [
        str(test.get("module") or "").strip() for test in tests
        if str(test.get("module") or "").strip().casefold()
        not in {"", "unassigned", "scenarios", "other"}
        and str(test.get("module") or "").strip() not in default_modules
    ]
    modules = default_modules + list(dict.fromkeys(custom_modules + explicit_modules))
    module_counts = {module: 0 for module in modules}
    for test in tests:
        test["display_module"] = _display_module(test)
        module_counts[test["display_module"]] = module_counts.get(test["display_module"], 0) + 1
    selected_paths = [str(test["yaml"]).replace("\\", "/") for test in tests]
    selected_set = {item.casefold() for item in selected_paths}
    scenarios = _scenario_paths()
    return {
        "key": path.stem,
        "name": data.get("suite") or path.stem,
        "tests": tests,
        "modules": modules,
        "module_counts": module_counts,
        "available": [item for item in scenarios if item.casefold() not in selected_set],
    }


def save_suite_tests(suite_name, ordered_yaml_paths, module_names=None):
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
    if module_names is not None:
        defaults = {"home", "premium", "login", "trending", "ebooks", "games"}
        custom_modules = []
        for submitted in module_names:
            module = " ".join(str(submitted).split()).strip()
            if not module or len(module) > 40 or module.casefold() in defaults:
                continue
            if module.casefold() not in {item.casefold() for item in custom_modules}:
                custom_modules.append(module)
        data["modules"] = custom_modules
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
