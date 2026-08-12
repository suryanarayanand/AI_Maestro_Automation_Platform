import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

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
SCENARIO_FOLDER = ROOT / "Expected"

SCREENSHOT_FOLDER = ROOT / ".maestro" / "screenshots" / "Screenshots"

BASELINE_FOLDER = (
    ROOT
    / ".maestro"
    / "screenshots"
    / "Baselines"
    / "Screenshots"
)

BASELINE_FOLDER.mkdir(parents=True, exist_ok=True)

# =====================================================
# Select Suite
# =====================================================

if len(sys.argv) > 1:
    suite_name = sys.argv[1].lower()
else:
    suite_name = "smoke"

suite_file = SUITE_FOLDER / f"{suite_name}.json"

if not suite_file.exists():
    print(f"\n❌ Suite '{suite_name}' not found.")
    sys.exit(1)

with open(suite_file, "r") as f:
    suite = json.load(f)

# =====================================================
# Execute
# =====================================================

print("=" * 80)
print(f"BASELINE CAPTURE : {suite['suite']}")
print("=" * 80)

passed = 0
failed = 0

suite_start = time.time()

for index, test in enumerate(suite["tests"], start=1):

    print("\n" + "=" * 80)
    print(f"[{index}/{len(suite['tests'])}]")
    print(f"Scenario : {test['id']}")
    print(f"Name     : {test['name']}")
    print("=" * 80)

    scenario = SCENARIO_FOLDER / test["yaml"]

    if not scenario.exists():
        print("❌ Scenario YAML not found.")
        failed += 1
        continue

    command = f'maestro test "{scenario}"'

    result = subprocess.run(
        command,
        shell=True,
        cwd=ROOT,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("❌ Maestro Execution Failed")
        print(result.stderr)
        failed += 1
        continue

    print("✅ Maestro Execution Completed")

    actual_folder = SCREENSHOT_FOLDER / test["id"]

    baseline_folder = BASELINE_FOLDER / test["id"]

    if not actual_folder.exists():
        print("⚠ No screenshots found.")
        failed += 1
        continue

    if baseline_folder.exists():
        shutil.rmtree(baseline_folder)

    shutil.copytree(actual_folder, baseline_folder)

    print(f"✅ Baseline Saved : {baseline_folder}")

    passed += 1

# =====================================================
# Summary
# =====================================================

duration = round(time.time() - suite_start, 2)

print("\n")
print("=" * 80)
print("BASELINE CAPTURE COMPLETED")
print("=" * 80)
print(f"Suite      : {suite['suite']}")
print(f"Passed     : {passed}")
print(f"Failed     : {failed}")
print(f"Duration   : {duration} sec")
print(f"Baselines  : {BASELINE_FOLDER}")
print("=" * 80)