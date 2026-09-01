import json
from pathlib import Path


root = Path(__file__).resolve().parents[1]
source = json.loads((root / "Suites" / "user_anonymous.json").read_text(encoding="utf-8"))
prefixes = ("ANON_GAMES_", "ANON_HAM_", "ANON_ACCOUNT_")
tests = [test for test in source.get("tests", []) if test.get("id", "").startswith(prefixes)]
expected = 36
if len(tests) != expected:
    raise SystemExit(f"Expected {expected} cases, found {len(tests)}")
suite = {
    "suite": "Anonymous — Games, Hamburger, Account Settings",
    "source_suite": "user_anonymous",
    "tests": tests,
}
target = root / "Suites" / "anonymous_games_hamburger_account.json"
target.write_text(json.dumps(suite, indent=4, ensure_ascii=False), encoding="utf-8")
print(target, len(tests))
