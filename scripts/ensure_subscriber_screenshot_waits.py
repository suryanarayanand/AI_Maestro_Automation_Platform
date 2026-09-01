"""Ensure Subscriber suite screenshots are taken only after UI loading settles."""

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "Suites" / "user_subscriber.json"


def main():
    suite = json.loads(SUITE.read_text(encoding="utf-8-sig"))
    paths = {
        ROOT / "Scenarios" / str(test["yaml"])
        for test in suite.get("tests", [])
        if test.get("yaml")
    }
    paths.update({
        ROOT / "Common" / "ASSERT_SUBSCRIBER_NO_MONETIZATION.yaml",
        ROOT / "Common" / "OPEN_SUBSCRIBER_HOME.yaml",
        ROOT / "Common" / "OPEN_SUBSCRIBER_GAMES.yaml",
        ROOT / "Common" / "SUBSCRIBER_LOGIN_ONCE.yaml",
        ROOT / "Common" / "SUBSCRIBER_LOGIN_CREDENTIALS_ONCE.yaml",
    })
    changed = []
    inserted = 0
    for path in sorted(paths):
        if not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        output = []
        file_insertions = 0
        for line in lines:
            match = re.match(r"^(\s*)-\s+takeScreenshot:", line)
            if match:
                previous = next((item for item in reversed(output) if item.strip()), "")
                expected = f"{match.group(1)}- waitForAnimationToEnd"
                if previous != expected:
                    output.append(expected)
                    inserted += 1
                    file_insertions += 1
            output.append(line)
        if file_insertions:
            path.write_text("\n".join(output) + "\n", encoding="utf-8")
            changed.append(path.relative_to(ROOT).as_posix())
    print(json.dumps({"inserted": inserted, "changed": changed}, indent=2))


if __name__ == "__main__":
    main()
