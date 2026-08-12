import re


def plan_category_navigation_case(case_id):
    """Build deterministic, reset-based routes for the generated category matrix case."""
    case_key = str(case_id).casefold()
    groups_by_case = {
        "sc_29_gen": {"india", "world", "sport"},
        "sc_29_india": {"india"},
        "sc_29_world": {"world"},
        "sc_29_sport": {"sport"},
    }
    groups = groups_by_case.get(case_key)
    if not groups:
        return None

    safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", str(case_id))
    commands = []

    def add(command, parameters=None):
        commands.append({"command": command, "parameters": parameters or {}})

    def open_menu():
        add("runFlow", {"path": "../Common/OPEN_HOME_FOR_LOCATOR_SMOKE.yaml"})
        add("extendedWaitUntil", {"visible": {"id": "nav_menu"}, "timeout": 15000})
        add("retry", {
            "maxRetries": 2,
            "commands": [
                {"tapOn": {"id": "nav_menu"}},
                {"extendedWaitUntil": {"visible": {"id": "screen_hamburger"}, "timeout": 10000}},
            ],
        })
        add("assertVisible", {"id": "screen_hamburger"})

    def route(parent, child, child_index=0):
        open_menu()
        add("tapOn", {"text": parent, "index": 0})
        parameters = {"text": child}
        if child_index:
            parameters["index"] = child_index
        add("tapOn", parameters)
        add("extendedWaitUntil", {"visible": {"id": "screen_section"}, "timeout": 20000})
        add("assertVisible", {"id": "screen_section"})
        add("swipe", {"direction": "UP"})
        add("waitForAnimationToEnd")
        label = re.sub(r"[^A-Za-z0-9]+", "_", f"{parent}_{child}").strip("_").lower()
        add("takeScreenshot", {"path": f"Screenshots/Generated/{safe_id}_{label}"})

    open_menu()
    add("takeScreenshot", {"path": f"Screenshots/Generated/{safe_id}_hamburger_menu"})
    if "india" in groups:
        route("India", "News")
        route("India", "India", child_index=1)
    if "world" in groups:
        route("World", "News")
        route("World", "India", child_index=1)
        route("World", "World", child_index=1)
    if "sport" in groups:
        route("Sport", "Sport", child_index=1)
        for child in ("Cricket", "Football", "Hockey", "Tennis", "Athletics", "Motorsport", "Races", "Other Sports"):
            route("Sport", child)
    return commands


def plan_complex_scenario(step, case_id="GENERATED"):
    """Expand recognized multi-action requirements into deterministic Maestro commands."""
    text = " ".join(str(step).split())
    lowered = text.lower()
    if not (
        "scroll" in lowered
        and re.search(r"tap(?:s|ping)? (?:the )?home tab", lowered)
        and ("top" in lowered or "scroll-to-top" in lowered)
    ):
        return None

    safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", str(case_id))
    return [
        {"command": "runFlow", "parameters": {"path": "../Common/OPEN_HOME_FOR_LOCATOR_SMOKE.yaml"}},
        {"command": "tapOn", "parameters": {"id": "nav_home"}},
        {"command": "assertVisible", "parameters": {"id": "screen_home"}},
        {"command": "swipe", "parameters": {"direction": "UP"}},
        {"command": "swipe", "parameters": {"direction": "UP"}},
        {"command": "waitForAnimationToEnd", "parameters": {}},
        {"command": "takeScreenshot", "parameters": {"path": f"Screenshots/Generated/{safe_id}_scrolled"}},
        {"command": "tapOn", "parameters": {"id": "nav_home"}},
        {"command": "waitForAnimationToEnd", "parameters": {}},
        {"command": "assertVisible", "parameters": {"id": "screen_home"}},
        {"command": "takeScreenshot", "parameters": {"path": f"Screenshots/Generated/{safe_id}_reset_top"}},
    ]
