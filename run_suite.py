import json
import os
import re
import shutil
import subprocess
import time
import sys
from pathlib import Path

from Utils.report_utils import (
    create_execution_folder,
    save_log
)

from Utils.excel_report import generate_excel_report
from Utils.html_report import generate_html_report
from Utils.ai_report import analyze_scenario, analyze_execution, save_ai_report
from Utils.ai_html_report import generate_ai_html_report
from Utils.master_report import generate_master_report
from Utils.master_html_report import generate_master_dashboard
from Utils.bug_summary_html import generate_bug_summary_html

from Utils.visual_report import (
    analyze_visual_scenario,
    analyze_visual_execution,
    save_visual_report
)

from Utils.visual_html_report import (
    generate_visual_html_report
)
from Utils.bug_summary import (
    generate_bug_summary,
    save_bug_summary
)

# =====================================================
# Project Paths
# =====================================================

ROOT = Path(__file__).resolve().parent
CONFIG_FILE = ROOT / "config.json"

# =====================================================
# Load Config
# =====================================================

with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

SUITE_FOLDER = ROOT / config["suiteFolder"]
SCENARIO_FOLDER = ROOT / config["scenarioFolder"]
REPORT_FOLDER = ROOT / config["reportFolder"]

REPORT_FOLDER.mkdir(exist_ok=True)


def collect_maestro_failure_screenshot(output, scenario_id):
    """Copy Maestro's automatic failure screenshot into the normal report input."""
    matches = re.findall(
        r"^[A-Za-z]:\\[^\r\n]*?\\\.maestro\\tests\\[^\r\n]+",
        output,
        flags=re.MULTILINE,
    )
    for raw_path in reversed(matches):
        artifact_folder = Path(raw_path.strip())
        if not artifact_folder.is_dir():
            continue
        screenshots = sorted(
            artifact_folder.glob("*.png"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        if screenshots:
            destination_folder = ROOT / config["screenshotFolder"] / scenario_id
            destination_folder.mkdir(parents=True, exist_ok=True)
            destination = destination_folder / f"{scenario_id}_Maestro_Failure.png"
            shutil.copy2(screenshots[0], destination)
            return destination
    return None


def test_credentials():
    credentials_path = ROOT / "credentials.local.json"
    credentials = {}
    if credentials_path.is_file():
        credentials = json.loads(credentials_path.read_text(encoding="utf-8"))
    return {
        "TEST_EMAIL": os.getenv("MAESTRO_TEST_EMAIL") or credentials.get("email"),
        "TEST_PASSWORD": os.getenv("MAESTRO_TEST_PASSWORD") or credentials.get("password"),
    }


def maestro_command(scenario):
    executable = shutil.which("maestro.bat" if os.name == "nt" else "maestro")
    if not executable:
        raise FileNotFoundError("Maestro executable was not found on PATH")
    command = [executable, "test"]
    for maestro_name, value in test_credentials().items():
        if value:
            command.extend(["-e", f"{maestro_name}={value}"])
    command.append(str(scenario))
    return command

# =====================================================
# Select Suite
# =====================================================

if len(sys.argv) > 1:
    suite_name = sys.argv[1].lower()
else:
    suite_name = "smoke"

suite_file = SUITE_FOLDER / f"{suite_name}.json"

if not suite_file.exists():
    print(f"\nSuite '{suite_name}' not found.")
    sys.exit(1)

with open(suite_file, "r") as f:
    suite = json.load(f)

# =====================================================
# Start Execution
# =====================================================

print("=" * 80)
print(f"Running {suite['suite']} Suite")
print("=" * 80)

results = []
visual_results = []
suite_start = time.time()

execution_folder = create_execution_folder(
    REPORT_FOLDER,
    suite["suite"]
)

# =====================================================
# Execute Scenarios
# =====================================================

for index, test in enumerate(suite["tests"], start=1):

    print("\n" + "=" * 80)
    print(f"[{index}/{len(suite['tests'])}]")
    print(f"Scenario ID : {test['id']}")
    print(f"Module      : {test['module']}")
    print(f"Priority    : {test['priority']}")
    print(f"Scenario    : {test['name']}")
    print("=" * 80)

    scenario = SCENARIO_FOLDER / test["yaml"]

    print(f"Scenario Exists : {scenario.exists()}")
    print(f"Scenario Path   : {scenario}")

    if not scenario.exists():

        print("❌ Scenario File Not Found")

        results.append({
            "id": test["id"],
            "module": test["module"],
            "name": test["name"],
            "status": "NOT FOUND",
            "duration": 0,
            "ai_pass": 0,
            "ai_fail": 0,
            "ai_errors": 0,
            "ai_details": []
        })

        continue

    print(f"Executing : {scenario.name}")

    start = time.time()

    result = subprocess.run(
        maestro_command(scenario),
        cwd=ROOT,
        capture_output=True,
        text=True
    )
    print("Return Code:", result.returncode)
    print("STDOUT length:", len(result.stdout))
    print("STDERR length:", len(result.stderr))

    duration = round(time.time() - start, 2)
    status = "PASS" if result.returncode == 0 else "FAIL"

    # Save Maestro Log
    log_file = save_log(
        execution_folder,
        test["id"],
        result.stdout,
        result.stderr
    )

    if status == "FAIL":
        failure_screenshot = collect_maestro_failure_screenshot(
            f"{result.stdout}\n{result.stderr}",
            test["id"],
        )
        if failure_screenshot:
            print("Failure Screenshot =", failure_screenshot)

    # ==========================================
    # AI Screenshot Analysis
    # ==========================================

   
    scenario_screenshot_folder = (
        ROOT /
        config["screenshotFolder"] /
        test["id"]
    )

    ai_pass = 0
    ai_fail = 0
    ai_errors = 0
    ai_details = []

    print("\n========== DEBUG ==========")
    print("ROOT =", ROOT)
    print("Screenshot Folder =", config["screenshotFolder"])
    print("Scenario Folder =", scenario_screenshot_folder)
    print("Exists =", scenario_screenshot_folder.exists())
    print("===========================\n")

    if scenario_screenshot_folder.exists():

        print("Files:")
        for f in scenario_screenshot_folder.glob("*"):
            print("  ", f.name)

        ai_result = analyze_scenario(
            scenario_screenshot_folder,
            execution_folder,
            test["id"]
        )

        ai_pass = ai_result["passed"]
        ai_fail = ai_result["failed"]
        ai_errors = ai_result["errors"]
        ai_details = ai_result["details"]

        print(
            f"AI Analysis : "
            f"{ai_pass} PASS | "
            f"{ai_fail} FAIL | "
            f"{ai_errors} ERROR"
        )

    else:
        print("No screenshots found for AI analysis.")

    print(f"\nStatus   : {status}")
    print(f"Duration : {duration} sec")
    print(f"Log File : {log_file.name}")

    if status == "FAIL":
        print("\n------ Maestro STDOUT ------")
        print(result.stdout)

        print("\n------ Maestro STDERR ------")
        print(result.stderr)

    results.append({
        "id": test["id"],
        "module": test["module"],
        "name": test["name"],
        "status": status,
        "duration": duration,
        "log_file": str(log_file),   # <-- Add this line
        "ai_pass": ai_pass,
        "ai_fail": ai_fail,
        "ai_errors": ai_errors,
        "ai_details": ai_details
    })
    baseline_folder = (
    ROOT /
    ".maestro" /
    "screenshots" /
    "Baselines" /
    "Screenshots" /
    test["id"]
    )

    actual_folder = (
    ROOT /
    config["screenshotFolder"] /
    test["id"]
)
# ==========================================
# Visual Regression Analysis
# ==========================================

baseline_folder = (
    ROOT /
    ".maestro" /
    "screenshots" /
    "Baselines" /
    "Screenshots" /
    test["id"]
)

actual_folder = (
    ROOT /
    config["screenshotFolder"] /
    test["id"]
)

if baseline_folder.exists() and actual_folder.exists():

    visual_result = analyze_visual_scenario(
        baseline_folder,
        actual_folder,
        execution_folder,
        test["id"]
    )
    print(visual_result)
    visual_results.append({

    "scenario": test["id"],

    "status": "PASS" if visual_result["failed"] == 0 else "FAIL",

    "passed": visual_result["passed"],

    "failed": visual_result["failed"],

    "details": visual_result["details"]

    })

    print(
        f"Visual Analysis : "
        f"{visual_result['passed']} PASS | "
        f"{visual_result['failed']} FAIL"
    )

else:

    print("Visual comparison skipped.")
# =====================================================
# Execution Summary
# =====================================================

suite_duration = round(time.time() - suite_start, 2)

passed = sum(1 for r in results if r["status"] == "PASS")
failed = sum(1 for r in results if r["status"] == "FAIL")
missing = sum(1 for r in results if r["status"] == "NOT FOUND")

print("\n")
print("=" * 80)
print("EXECUTION SUMMARY")
print("=" * 80)

print(f"Suite           : {suite['suite']}")
print(f"Total Tests     : {len(results)}")
print(f"Passed          : {passed}")
print(f"Failed          : {failed}")
print(f"Not Found       : {missing}")
print(f"Execution Time  : {suite_duration:.2f} sec")

print("\nDetailed Results")
print("-" * 80)

for r in results:

    print(
        f"{r['id']:<10}"
        f"{r['status']:<12}"
        f"{str(r['duration'])+'s':<12}"
        f"{r['module']:<15}"
        f"{r['name']}"
    )

print("=" * 80)
print("Suite Execution Completed")
print("=" * 80)

generate_excel_report(
    results=results,
    suite_name=suite["suite"],
    execution_time=suite_duration,
    report_folder=execution_folder
)
generate_html_report(
    results=results,
    suite_name=suite["suite"],
    execution_time=suite_duration,
    report_folder=execution_folder
)

# =====================================================
# AI Report (generated exactly once, after every scenario has run)
# =====================================================

ai_summary = analyze_execution(results)
ai_report_file = save_ai_report(ai_summary, execution_folder)
ai_html = generate_ai_html_report(ai_report_file, execution_folder)

visual_summary = analyze_visual_execution(visual_results)

visual_report_file = save_visual_report(
    visual_summary,
    execution_folder
)

visual_html = generate_visual_html_report(
    visual_report_file,
    execution_folder
)

print("\n" + "=" * 80)
print("REPORTS GENERATED")
print("=" * 80)

print(f"Folder         : {execution_folder}")
print(f"Excel Report   : {execution_folder / 'Dashboard.xlsx'}")
print(f"HTML Report    : {execution_folder / 'Dashboard.html'}")
print(f"AI Report        : {ai_report_file}")
print(f"AI HTML Report   : {ai_html}")
print(f"Visual Report    : {visual_report_file}")
print(f"Visual HTML      : {visual_html}")


# =====================================================
# Bug Summary
# =====================================================

bug_summary = generate_bug_summary(
    results,
    ai_summary,
    visual_summary,
    suite["suite"],
    suite_duration
)

bug_summary_file = save_bug_summary(
    bug_summary,
    execution_folder
)
bug_summary_html = generate_bug_summary_html(
    bug_summary_file,
    execution_folder
)

print(f"Bug Summary HTML : {bug_summary_html}")
print(f"Bug Summary     : {bug_summary_file}")


# =====================================================
# Generate Master Dashboard
# =====================================================

REPORT_ROOT = ROOT / config["reportFolder"]

master_json = generate_master_report(REPORT_ROOT)

generate_master_dashboard(
    master_json,
    REPORT_ROOT
)
