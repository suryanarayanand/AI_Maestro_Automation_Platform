import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "Scenarios" / "OptimizedLocatorSmoke"
BASELINE_OUTPUT = ROOT / "Scenarios" / "ProductionBaseline"

PAGES = [
    ("Videos", "screen_home", "home", None),
    ("Photos", "screen_home", "home", None),
    ("Podcast", "screen_home", "home", None),
    ("India", "screen_home", "home", None),
    ("World", "screen_home", "home", None),
    ("Editorial", "screen_home", "home", None),
    ("Opinion", "screen_home", "home", None),
    ("Sports", "screen_home", "shifted", None),
    ("Business", "screen_home", "shifted", None),
    ("Sci-Tech", "screen_section", "child", ("Science", False)),
    ("Entertainment", "screen_section", "child", ("Entertainment", True)),
    ("Books", "screen_section", "child", ("Books", True)),
    ("Food", "screen_section", "child", ("Life & Style", False)),
    ("Latest News", "screen_section", "child", ("News", True)),
]


def slug(value):
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def render(page, container, route, parent):
    actual = "News" if page == "Latest News" else page
    lines = [
        "appId: com.mobstac.thehindu",
        "tags:",
        "  - locator-smoke",
        f"  - {slug(page)}",
        "---",
        "- runFlow: ../Common/OPEN_HOME_FOR_LOCATOR_SMOKE.yaml",
    ]
    if route == "home":
        lines += ["- tapOn:", f'    text: "{actual}"']
    elif route == "shifted":
        lines += [
            "- repeat:", "    times: 5", "    commands:",
            "      - swipe:", "          direction: LEFT",
            "      - waitForAnimationToEnd",
            "- extendedWaitUntil:", "    visible:", f'      text: "{actual}"',
            "    timeout: 15000", "- tapOn:", f'    text: "{actual}"',
        ]
    else:
        category, duplicate = parent
        lines += [
            "- tapOn:", '    id: "nav_menu"',
            "- extendedWaitUntil:", "    visible:", '      id: "screen_hamburger"',
            "    timeout: 15000",
            "- scrollUntilVisible:", "    element:", f'      text: "{category}"',
            "    direction: DOWN", "    timeout: 30000",
            "- tapOn:", f'    text: "{category}"',
            "- extendedWaitUntil:", "    visible:", f'      text: "{actual}"',
            "    timeout: 15000",
        ]
        lines += ["- tapOn:", f'    text: "{actual}"']
        if duplicate:
            lines.append("    index: 1")
    lines += [
        "- waitForAnimationToEnd",
        "- extendedWaitUntil:", "    visible:", f'      id: "{container}"',
        "    timeout: 20000",
        "- assertVisible:", f'    id: "{container}"',
        "- assertVisible:", f'    text: "{actual}"',
        f'- takeScreenshot: "Screenshots/LocatorSmoke/{slug(page)}_page"',
        "",
    ]
    return "\n".join(lines)


def render_baseline(page, route, parent):
    """Production-safe navigation: live builds do not expose internal test IDs."""
    actual = "News" if page == "Latest News" else page
    lines = [
        "appId: com.mobstac.thehindu", "tags:", "  - baseline",
        f"  - {slug(page)}", "---",
        "- runFlow: ../Common/OPEN_HOME_FOR_BASELINE.yaml",
    ]
    tab_numbers = {
        "Videos": 1, "Photos": 2, "Podcast": 3, "India": 5,
        "World": 6, "Editorial": 7, "Opinion": 8, "Sports": 9,
        "Business": 10,
    }
    tab_text = f"{actual}\\nTab {tab_numbers[page]} of 15" if page in tab_numbers else actual
    if route == "home":
        lines += ["- tapOn:", f'    text: "{tab_text}"']
    elif route == "shifted":
        lines += [
            "- repeat:", "    times: 5", "    commands:",
            "      - swipe:", "          direction: LEFT",
            "      - waitForAnimationToEnd",
            "- extendedWaitUntil:", "    visible:", f'      text: "{tab_text}"',
            "    timeout: 15000", "- tapOn:", f'    text: "{tab_text}"',
        ]
    else:
        category, duplicate = parent
        lines += [
            "- tapOn:", '    point: "6%,10%"',
            "- extendedWaitUntil:", "    visible:", f'      text: "{category}"',
            "    timeout: 15000",
            "- scrollUntilVisible:", "    element:", f'      text: "{category}"',
            "    direction: DOWN", "    timeout: 30000",
            "- tapOn:", f'    text: "{category}"',
            "- extendedWaitUntil:", "    visible:", f'      text: "{actual}"',
            "    timeout: 15000",
        ]
        if duplicate:
            # Production exposes only the expandable parent to text matching.
            child_point = "15%,56%" if page == "Entertainment" else "15%,62%"
            lines += ["- tapOn:", f'    point: "{child_point}"']
        else:
            lines += ["- tapOn:", f'    text: "{actual}"']
    lines += [
        "- waitForAnimationToEnd",
        "- extendedWaitUntil:", "    visible:", f'      text: "{tab_text}"',
        "    timeout: 20000",
        "- assertVisible:", f'    text: "{tab_text}"',
        f'- takeScreenshot: "Screenshots/LocatorSmoke/{slug(page)}_page"', "",
    ]
    return "\n".join(lines)


def build():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    BASELINE_OUTPUT.mkdir(parents=True, exist_ok=True)
    tests = []
    baseline_tests = []
    for page, container, route, parent in PAGES:
        name = slug(page)
        filename = f"LOC_{name}.yaml"
        (OUTPUT / filename).write_text(
            render(page, container, route, parent), encoding="utf-8"
        )
        tests.append({
            "id": f"LOC_{name.upper()}",
            "module": "Validated Section Locators",
            "priority": "P1",
            "name": f"Validated locator smoke - {page}",
            "yaml": f"OptimizedLocatorSmoke/{filename}",
        })
        (BASELINE_OUTPUT / filename).write_text(
            render_baseline(page, route, parent), encoding="utf-8"
        )
        baseline_tests.append({
            "id": f"LOC_{name.upper()}",
            "module": "Production Reference Screenshots",
            "priority": "P1",
            "name": f"Production baseline - {page}",
            "yaml": f"ProductionBaseline/{filename}",
        })
    suite = {"suite": "LocatorSmoke", "tests": tests}
    (ROOT / "Suites" / "LocatorSmoke.json").write_text(
        json.dumps(suite, indent=4), encoding="utf-8"
    )
    (ROOT / "Suites" / "baseline.json").write_text(
        json.dumps({"suite": "baseline", "tests": baseline_tests}, indent=4),
        encoding="utf-8",
    )
    return len(tests)


if __name__ == "__main__":
    print(f"Generated {build()} optimized locator smoke cases")
