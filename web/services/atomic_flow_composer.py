"""Compose complete, reviewable Maestro flows from atomic catalogue requirements."""

import json
import re
from pathlib import Path

APP_ID = "com.mobstac.thehindu"
ROOT = Path(__file__).resolve().parents[2]


def _validated_ids():
    data = json.loads(
        (ROOT / "LocatorRepository" / "validated_locator_repository.json").read_text(encoding="utf-8")
    )
    return {
        item.get("locator", {}).get("value")
        for item in data
        if item.get("locator", {}).get("type") == "id"
    }


def _assert_grounded(commands):
    validated = _validated_ids()
    used = set()

    def visit(value):
        if isinstance(value, dict):
            if "id" in value:
                used.add(value["id"])
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(commands)
    missing = sorted(used - validated)
    if missing:
        raise ValueError("Flow requires unvalidated locator IDs: " + ", ".join(missing))


def _scalar(value):
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def _write_mapping(lines, mapping, indent):
    prefix = " " * indent
    for key, value in mapping.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            _write_mapping(lines, value, indent + 2)
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}:")
            _write_list(lines, value, indent + 2)
        else:
            lines.append(f"{prefix}{key}: {_scalar(value)}")


def _write_list(lines, values, indent=0):
    prefix = " " * indent
    for value in values:
        if not isinstance(value, dict):
            lines.append(f"{prefix}- {_scalar(value)}")
            continue
        key, nested = next(iter(value.items()))
        if isinstance(nested, dict) and nested:
            lines.append(f"{prefix}- {key}:")
            _write_mapping(lines, nested, indent + 4)
        elif isinstance(nested, dict):
            lines.append(f"{prefix}- {key}")
        else:
            lines.append(f"{prefix}- {key}: {_scalar(nested)}")


def _render(metadata, commands, source, memory_count):
    lines = [f"appId: {metadata['appId']}", "tags:"]
    lines.extend(f"  - {tag}" for tag in metadata["tags"])
    if metadata.get("env"):
        lines.append("env:")
        _write_mapping(lines, metadata["env"], 2)
    lines.extend([
        "---", f"# Generated from: {source}",
        f"# Grounding: validated locator repository; {memory_count} matching App Memory records.",
    ])
    _write_list(lines, commands)
    return "\n".join(lines) + "\n"


def _wait_visible(selector, timeout=20000):
    return {"extendedWaitUntil": {"visible": selector, "timeout": timeout}}


def _setup(state):
    flow = "OPEN_SUBSCRIBER_HOME.yaml" if state == "SUBSCRIBER" else "OPEN_ANONYMOUS_HOME.yaml"
    return [{"runFlow": f"../../Common/{flow}"}]


def _state_assertions(state):
    """Prove the entitlement state before executing the scenario route."""
    if state == "SUBSCRIBER":
        return [
            {"assertNotVisible": {"text": "SUBSCRIBE"}},
            {"assertNotVisible": {"text": "ADVERTISEMENT"}},
            {"assertNotVisible": {"id": "aw0"}},
        ]
    return [
        {"assertVisible": {"text": "SUBSCRIBE"}},
        {"repeat": {
            "while": {"notVisible": {"text": "ADVERTISEMENT"}},
            "times": 8,
            "commands": [
                {"swipe": {"direction": "UP"}},
                {"waitForAnimationToEnd": {}},
            ],
        }},
        {"assertVisible": {"text": "ADVERTISEMENT"}},
        {"tapOn": {"id": "nav_home"}},
        _wait_visible({"id": "screen_home"}, 15000),
    ]


def _article_open():
    return [
        {"tapOn": {"id": "article_card", "index": 0}},
        {"waitForAnimationToEnd": {"timeout": 8000}},
        {"tapOn": {"text": "Close sheet", "optional": True}},
        {"tapOn": {"text": "Interstitial close button", "optional": True}},
        _wait_visible({"id": "screen_article_detail"}, 25000),
        {"assertVisible": {"id": "screen_article_detail"}},
    ]


def _photos_flow(text):
    commands = [
        {"tapOn": {"text": "Photos"}},
        _wait_visible({"text": "[0-9]+"}, 15000),
        {"assertVisible": {"text": "[0-9]+"}},
    ]
    if re.search(r"(?:open|tap|article|story|pager|detail)", text, re.I):
        commands.extend([
            {"tapOn": {"text": "[0-9]+", "index": 0}},
            {"waitForAnimationToEnd": {"timeout": 8000}},
            {"tapOn": {"text": "Close sheet", "optional": True}},
            _wait_visible({"id": "screen_article_detail"}, 20000),
            {"assertVisible": {"id": "screen_article_detail"}},
            {"assertVisible": {"text": "[0-9]+/[0-9]+"}},
        ])
    else:
        commands.append({"assertVisible": {"id": "screen_home"}})
    return commands


def _ai_summary_flow(state, text):
    commands = _article_open()
    if state == "SUBSCRIBER":
        commands.extend([
            {"swipe": {"direction": "LEFT"}},
            _wait_visible({"text": "Summary"}, 20000),
            {"assertVisible": {"text": "Summary"}},
            {"assertVisible": {"text": "Article FAQs"}},
            {"assertVisible": {"text": "(?s).*automatically generated by an AI tool.*"}},
        ])
    else:
        commands.extend([
            {"tapOn": {"text": "AI Summary|Summary", "optional": True}},
            _wait_visible({"text": "Login|Subscribe|Go beyond the headline.*"}, 15000),
            {"assertVisible": {"text": "Login|Subscribe|Go beyond the headline.*"}},
        ])
    return commands


def _logout_flow():
    return [
        {"tapOn": {"id": "nav_account"}},
        _wait_visible({"id": "screen_user_menu"}, 15000),
        {"scrollUntilVisible": {
            "element": {"text": "Logout|Log out|LOGOUT|Log Out"}, "direction": "DOWN"
        }},
        {"tapOn": {"text": "Logout|Log out|LOGOUT|Log Out"}},
        {"tapOn": {"text": "Logout|Log out|Yes|OK|Confirm", "optional": True}},
        {"waitForAnimationToEnd": {"timeout": 5000}},
        _wait_visible({"id": "nav_home"}, 15000),
        {"tapOn": {"id": "nav_account"}},
        _wait_visible({"id": "screen_user_menu"}, 15000),
        {"assertVisible": {"text": "Login"}},
        {"assertVisible": {"text": "Create account"}},
    ]


def _article_subscribe_login_flow():
    return _article_open() + [
        {"runFlow": "../../Common/LOGIN_FROM_ARTICLE_SUBSCRIBE.yaml"},
        {"assertVisible": {"id": "screen_article_detail"}},
    ]


def _generic_flow(text):
    lowered = text.casefold()
    if "pull to refresh" in lowered:
        return [
            {"swipe": {"start": "50%, 25%", "end": "50%, 80%", "duration": 800}},
            {"waitForAnimationToEnd": {"timeout": 8000}},
            _wait_visible({"id": "screen_home"}, 20000),
            {"assertVisible": {"id": "screen_home"}},
            {"assertVisible": {"id": "nav_menu"}},
            {"assertVisible": {"text": "The Hindu"}},
            {"assertVisible": {"id": "article_card", "index": 0}},
            {"takeScreenshot": "Screenshots/Generated/home_after_refresh"},
        ]
    if "article" in lowered:
        return _article_open()
    if any(term in lowered for term in ("account", "user menu", "setting")):
        return [
            {"tapOn": {"id": "nav_account"}},
            _wait_visible({"id": "screen_user_menu"}, 15000),
            {"assertVisible": {"id": "screen_user_menu"}},
        ]
    if "hamburger" in lowered or "section" in lowered:
        return [
            {"tapOn": {"id": "nav_menu"}},
            _wait_visible({"id": "screen_hamburger"}, 15000),
            {"assertVisible": {"id": "screen_hamburger"}},
        ]
    if "home" in lowered or "content" in lowered:
        return [
            _wait_visible({"id": "screen_home"}, 20000),
            {"assertVisible": {"id": "screen_home"}},
            {"swipe": {"direction": "UP"}},
            {"waitForAnimationToEnd": {"timeout": 5000}},
            {"assertVisible": {"id": "screen_home"}},
        ]
    raise ValueError(
        "This requirement has no grounded in-app route yet. Add a validated locator or "
        "select a reusable flow before generating; no placeholder YAML was created."
    )


def compose_atomic_flow(step):
    from web.services.adaptive_test_agent import AdaptiveTestAgent

    text = re.sub(r"^.*?Action:\s*", "", step["source_text"], flags=re.I).strip()
    lowered = text.casefold()
    external = ("play store", "appstore", "test flight", "diawi", "notification tray", "compared to the web")
    if any(term in lowered for term in external):
        raise ValueError(
            "This scenario depends on external test data or infrastructure and cannot be "
            "grounded as an in-app Maestro flow yet."
        )
    state = step["user_state"].upper()
    article_subscribe_login = (
        "article" in lowered
        and "subscribe" in lowered
        and bool(re.search(r"\b(?:log(?:s|ged)?\s*in|login|sign(?:s|ed)?\s*in|signin)\b", lowered))
    )
    if "logout" in lowered or "log out" in lowered:
        state = "SUBSCRIBER"
        commands = _setup(state) + _state_assertions(state) + _logout_flow()
    elif article_subscribe_login:
        state = "ANONYMOUS"
        commands = _setup(state) + _state_assertions(state) + _article_subscribe_login_flow()
    elif "ai summary" in lowered:
        commands = _setup(state) + _state_assertions(state) + _ai_summary_flow(state, text)
    elif "photo" in lowered:
        commands = _setup(state) + _state_assertions(state) + _photos_flow(text)
    else:
        commands = _setup(state) + _state_assertions(state) + _generic_flow(text)

    _assert_grounded(commands)
    memory = AdaptiveTestAgent().retrieve(
        [step.get("scenario", ""), text], limit=12, user_state=state
    )
    accepted_memory = sum(
        bool(item.get("validated") or item.get("evidence_type") == "accepted_learning")
        for item in memory
    )

    tags = list(dict.fromkeys([*step.get("tags_list", []), "generated", "review-required"]))
    metadata = {"appId": APP_ID, "tags": tags}
    return _render(metadata, commands, text, accepted_memory)
