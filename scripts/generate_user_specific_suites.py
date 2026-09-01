import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCENARIOS = ROOT / "Scenarios"
SUITES = ROOT / "Suites"

ANONYMOUS = re.compile(
    r"anonymous|ananymous|ananoymous|anonyous|anonymous_account|free user",
    re.IGNORECASE,
)
SUBSCRIBER = re.compile(
    r"subscriber|subscribed|subscription account|premium subscriber|open_subscriber",
    re.IGNORECASE,
)
MIXED = re.compile(
    r"subscriber-to-anonymous|subscribed.*logout.*anonymous|subscriber.*logout.*anonymous",
    re.IGNORECASE | re.DOTALL,
)


def scenario_entry(path: Path) -> dict:
    relative = path.relative_to(SCENARIOS).as_posix()
    module = path.parent.name if path.parent != SCENARIOS else "Scenarios"
    identifier = path.stem if path.parent == SCENARIOS else f"{module}__{path.stem}"
    return {
        "id": identifier,
        "module": module,
        "priority": "P2",
        "name": identifier.replace("_", " "),
        "yaml": relative,
    }


groups = {"anonymous": [], "subscriber": [], "mixed": [], "unclassified": []}

for path in sorted(SCENARIOS.rglob("*.yaml"), key=lambda item: item.as_posix().lower()):
    content = path.read_text(encoding="utf-8-sig", errors="replace")
    evidence = f"{path.stem}\n{content}"
    has_anonymous = bool(ANONYMOUS.search(evidence))
    has_subscriber = bool(SUBSCRIBER.search(evidence))

    if MIXED.search(evidence) or (has_anonymous and has_subscriber):
        group = "mixed"
    elif has_subscriber:
        group = "subscriber"
    elif has_anonymous:
        group = "anonymous"
    else:
        group = "unclassified"

    groups[group].append(scenario_entry(path))

suite_definitions = {
    "user_anonymous": ("Anonymous User Cases", groups["anonymous"]),
    "user_subscriber": ("Subscriber User Cases", groups["subscriber"]),
    "user_mixed_subscriber_to_anonymous": (
        "Subscriber to Anonymous Mixed Cases",
        groups["mixed"],
    ),
}

SUITES.mkdir(exist_ok=True)
for filename, (title, tests) in suite_definitions.items():
    destination = SUITES / f"{filename}.json"
    destination.write_text(
        json.dumps({"suite": title, "tests": tests}, indent=2) + "\n",
        encoding="utf-8",
    )

audit = {
    "counts": {name: len(tests) for name, tests in groups.items()},
    "unclassified": groups["unclassified"],
}
(SUITES / "user_specific_classification_audit.json").write_text(
    json.dumps(audit, indent=2) + "\n",
    encoding="utf-8",
)

print(json.dumps(audit["counts"], indent=2))
