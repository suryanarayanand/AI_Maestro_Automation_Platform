import argparse
import json
from pathlib import Path

from large_workbook_reader import LargeWorkbookReader


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EXCEL = ROOT / "Uploads" / "TH App Testing Scenarios_AutomationCopy.xlsx"
DEFAULT_OUTPUT = ROOT / "Scenarios" / "THExcelPilot"


PILOT_CASES = {
    "TH_1177": {
        "filename": "TH_1177_bottom_navigation.yaml",
        "tags": ["excel", "pilot", "smoke", "bottom-tabs"],
        "commands": [
            {"tapOn": {"id": "nav_home"}},
            {"assertVisible": {"id": "screen_home"}},
            {"takeScreenshot": "TH_1177_home"},
            {"tapOn": {"id": "nav_trending"}},
            {"assertVisible": {"id": "screen_trending"}},
            {"takeScreenshot": "TH_1177_trending"},
            {"tapOn": {"id": "nav_premium"}},
            {"assertVisible": {"id": "screen_premium"}},
            {"takeScreenshot": "TH_1177_premium"},
            {"tapOn": {"id": "nav_ebooks"}},
            {"assertVisible": {"id": "screen_ebooks"}},
            {"takeScreenshot": "TH_1177_ebooks"},
            {"tapOn": {"id": "nav_games"}},
            {"assertVisible": {"id": "screen_games"}},
            {"takeScreenshot": "TH_1177_games"},
        ],
    },
    "TH_0082": {
        "filename": "TH_0082_hamburger_sections.yaml",
        "tags": ["excel", "pilot", "smoke", "hamburger"],
        "commands": [
            {"tapOn": {"id": "nav_menu"}},
            {"assertVisible": {"id": "screen_hamburger"}},
            {"assertVisible": {"text": "Sport"}},
            {"assertVisible": {"text": "Business"}},
            {"tapOn": {"text": "Sport"}},
            {"assertVisible": {"id": "screen_section"}},
            {"takeScreenshot": "TH_0082_sport"},
            {"tapOn": {"id": "nav_menu"}},
            {"assertVisible": {"id": "screen_hamburger"}},
            {"tapOn": {"text": "Business"}},
            {"assertVisible": {"id": "screen_section"}},
            {"takeScreenshot": "TH_0082_business"},
        ],
    },
}


def _yaml_value(value, indent=0):
    prefix = " " * indent
    if isinstance(value, dict):
        lines = []
        for key, child in value.items():
            if isinstance(child, dict):
                lines.append(f"{prefix}{key}:")
                lines.extend(_yaml_value(child, indent + 2))
            else:
                lines.append(f'{prefix}{key}: "{child}"')
        return lines
    return [f'{prefix}"{value}"']


def render(case, design, app_id="com.mobstac.thehindu"):
    lines = [f"appId: {app_id}", "tags:"]
    lines.extend(f"  - {tag}" for tag in design["tags"])
    lines.extend([
        "---",
        f"# Excel source: {case['id']} | {case['module']} | {case['name']}",
        "# Validation requirement:",
    ])
    for point in case["validation_points"]:
        clean = point["description"].replace("\n", " ")
        lines.append(f"# - {clean}")
    lines.extend([
        "- launchApp:",
        "    clearState: false",
        "- runFlow:",
        "    when:",
        '      visible: "Skip"',
        "    commands:",
        '      - tapOn: "Skip"',
        "- extendedWaitUntil:",
        "    visible:",
        '      id: "screen_home"',
        "    timeout: 15000",
    ])
    for command in design["commands"]:
        key, value = next(iter(command.items()))
        if isinstance(value, dict):
            lines.append(f"- {key}:")
            lines.extend(_yaml_value(value, 4))
        else:
            lines.append(f'- {key}: "Screenshots/THExcelPilot/{value}"')
        if key == "tapOn":
            lines.append("- waitForAnimationToEnd")
    lines.append("")
    return "\n".join(lines)


def generate(excel_path=DEFAULT_EXCEL, output_dir=DEFAULT_OUTPUT):
    cases = {case["id"]: case for case in LargeWorkbookReader().read_groups(excel_path)}
    missing = sorted(set(PILOT_CASES).difference(cases))
    if missing:
        raise ValueError("Pilot source cases missing from workbook: " + ", ".join(missing))

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    suite_tests = []
    for case_id, design in PILOT_CASES.items():
        case = cases[case_id]
        destination = output_dir / design["filename"]
        destination.write_text(render(case, design), encoding="utf-8")
        suite_tests.append({
            "id": case_id,
            "module": case["module"],
            "priority": "P1",
            "name": case["name"],
            "yaml": f"THExcelPilot/{design['filename']}",
        })

    suite = {"suite": "THExcelPilot", "tests": suite_tests}
    suite_path = ROOT / "Suites" / "THExcelPilot.json"
    suite_path.write_text(json.dumps(suite, indent=4), encoding="utf-8")
    return [output_dir / item["filename"] for item in PILOT_CASES.values()], suite_path


def main():
    parser = argparse.ArgumentParser(description="Generate traceable TH workbook pilot YAML")
    parser.add_argument("--excel", default=str(DEFAULT_EXCEL))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    files, suite = generate(Path(args.excel), Path(args.output))
    for path in files:
        print(path)
    print(suite)


if __name__ == "__main__":
    main()
