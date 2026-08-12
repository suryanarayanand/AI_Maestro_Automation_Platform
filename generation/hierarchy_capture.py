import argparse
import json
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def safe_name(value):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_") or "screen"


def main():
    parser = argparse.ArgumentParser(description="Capture the current Maestro device hierarchy as JSON.")
    parser.add_argument("name", help="Logical screen/checkpoint name, such as home_top")
    parser.add_argument("--device", help="ADB device id; Maestro selects the only connected device when omitted")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "Hierarchies")
    args = parser.parse_args()

    executable = shutil.which("maestro.bat" if os.name == "nt" else "maestro")
    if not executable:
        raise SystemExit("Maestro executable was not found on PATH")

    command = [executable]
    if args.device:
        command.extend(["--udid", args.device])
    command.extend(["hierarchy", "--no-ansi", "--no-reinstall-driver"])
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(result.stderr or result.stdout or "Hierarchy capture failed")

    start, end = result.stdout.find("{"), result.stdout.rfind("}")
    if start < 0 or end < start:
        raise SystemExit("Maestro hierarchy output did not contain JSON")
    hierarchy = json.loads(result.stdout[start:end + 1])

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = args.output_dir / f"{safe_name(args.name)}_{timestamp}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(hierarchy, indent=2, ensure_ascii=False), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
