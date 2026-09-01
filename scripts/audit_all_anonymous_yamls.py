import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from web.services.adaptive_test_agent import reusable_yaml
from web.services.yaml_editor_service import validate_maestro_yaml


SUITE_PATH = ROOT / "Suites" / "user_anonymous.json"
SCENARIOS = ROOT / "Scenarios"
EXPECTED_MODULES = {
    "ANON_HOME_": "Home",
    "ANON_TREND_": "Trending",
    "ANON_PREM_": "Premium",
    "ANON_EBOOK_": "eBooks",
    "ANON_GAMES_": "Games",
    "ANON_HAM_": "Hamburger Menu",
    "ANON_ACCOUNT_": "Account Settings",
    "ANON_VIDEO_": "Videos",
    "ANON_PHOTO_": "Photos Quick Access",
    "ANON_EDITORIAL_": "Editorial Quick Access",
    "ANON_OPINION_": "Opinion Quick Access",
    "ANON_PODCAST_": "Podcast Quick Access",
}


def expected_module(case_id):
    return next((module for prefix, module in EXPECTED_MODULES.items() if case_id.startswith(prefix)), None)


suite = json.loads(SUITE_PATH.read_text(encoding="utf-8"))
tests = suite.get("tests", [])
errors = defaultdict(list)
warnings = defaultdict(list)

id_counts = Counter(item.get("id") for item in tests)
yaml_counts = Counter(item.get("yaml") for item in tests)
for case_id, count in id_counts.items():
    if count > 1:
        errors[case_id].append(f"duplicate suite id ({count})")
for filename, count in yaml_counts.items():
    if count > 1:
        errors[filename].append(f"same YAML assigned to {count} suite cases")

suite_files = set()
for item in tests:
    case_id = item.get("id", "<missing-id>")
    filename = item.get("yaml") or f"{case_id}.yaml"
    suite_files.add(filename)
    path = SCENARIOS / filename
    module = item.get("module")
    section = item.get("section")
    expected = expected_module(case_id)
    if not case_id.startswith("ANON_"):
        errors[case_id].append("non-anonymous case id in anonymous suite")
    if expected and module != expected:
        errors[case_id].append(f"module is {module!r}; expected {expected!r}")
    if section != module:
        warnings[case_id].append(f"section {section!r} differs from module {module!r}")
    if str(item.get("user_state", "")).upper() != "ANONYMOUS":
        errors[case_id].append(f"user_state is {item.get('user_state')!r}")
    if not path.is_file():
        errors[case_id].append(f"missing scenario file {filename}")
        continue
    text = path.read_text(encoding="utf-8-sig")
    if not re.search(r"(?m)^appId:\s*com\.mobstac\.thehindu\s*$", text):
        errors[case_id].append("missing/wrong appId")
    if not re.search(r"(?mi)^tags:.*anonymous", text):
        warnings[case_id].append("anonymous tag missing")
    try:
        validate_maestro_yaml(text)
    except Exception as exc:
        errors[case_id].append(f"YAML validation: {exc}")
    try:
        if not reusable_yaml(text):
            errors[case_id].append("not reusable Maestro structure")
    except Exception as exc:
        errors[case_id].append(f"structure check failed: {exc}")
    for flow in re.findall(r'(?m)^\s*-?\s*runFlow:\s*["\']?([^"\'\r\n{}]+\.ya?ml)', text):
        flow = flow.strip()
        if "${" in flow:
            continue
        target = (path.parent / flow).resolve()
        if not target.is_file():
            errors[case_id].append(f"missing runFlow target: {flow}")
    if re.search(r"(?i)TODO|TBD|PLACEHOLDER|replace[_ -]?me|dummy", text):
        errors[case_id].append("contains TODO/placeholder content")
    if re.search(r"(?i)subscriber_email|subscriber_password|logged.in subscriber", text):
        errors[case_id].append("contains subscriber-state credential/session reference")
    if not re.search(r"(?m)^\s*-\s*(runFlow|launchApp):", text):
        warnings[case_id].append("no explicit launch/setup flow")
    if not re.search(r"(?m)^\s*-\s*(assertVisible|assertNotVisible|extendedWaitUntil|scrollUntilVisible):", text):
        errors[case_id].append("no executable assertion")
    if not re.search(r"(?m)^\s*-\s*takeScreenshot:", text):
        warnings[case_id].append("no screenshot evidence")
    optional_count = len(re.findall(r"(?i)optional:\s*true", text))
    if optional_count >= 3:
        warnings[case_id].append(f"uses {optional_count} optional commands; may hide failures")
    point_count = len(re.findall(r"(?m)point:\s*[\"']?[0-9]+%?,[0-9]+%?", text))
    if point_count >= 3:
        warnings[case_id].append(f"uses {point_count} coordinate taps; locator stability review needed")

all_anon_files = {p.name for p in SCENARIOS.glob("ANON_*.yaml")}
orphans = sorted(all_anon_files - suite_files)

print(json.dumps({
    "suite_cases": len(tests),
    "scenario_files": len(all_anon_files),
    "blocking_case_count": len(errors),
    "warning_case_count": len(warnings),
    "orphan_files": orphans,
    "errors": dict(sorted(errors.items())),
    "warnings": dict(sorted(warnings.items())),
}, indent=2))
