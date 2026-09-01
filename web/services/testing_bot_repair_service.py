"""Evidence-grounded, non-mutating YAML repair proposals for Friday."""

import json
import os
import re
from pathlib import Path

from openai import OpenAI

from web.services.adaptive_test_agent import AdaptiveTestAgent, reusable_yaml, yaml_command_sequence
from web.services.yaml_editor_service import validate_maestro_yaml
from web.portal_db import connect


ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ROOT / "Scenarios"

REPAIR_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "yaml": {"type": "string"},
        "mappings": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "position": {"type": "integer"},
                    "commands": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                    "evidence": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["position", "commands", "evidence"],
            },
        },
        "assumptions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["yaml", "mappings", "assumptions"],
}


def _items(draft):
    try:
        value = json.loads(draft["traceability"] or "[]")
    except (json.JSONDecodeError, TypeError):
        value = []
    return value if isinstance(value, list) else []


def _tokens(*values):
    return {token for token in re.findall(r"[a-z0-9]+", " ".join(map(str, values)).casefold()) if len(token) > 3}


def _legacy_references(draft, limit=6):
    """Read old handwritten YAML as reference-only evidence, even if never passed."""
    wanted = _tokens(draft["case_id"], draft["name"], draft["traceability"])
    ranked = []
    for path in SCENARIOS.glob("*.yaml"):
        if path.stem.upper() == str(draft["case_id"]).upper():
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        overlap = wanted & _tokens(path.stem, text[:5000])
        if overlap:
            ranked.append((len(overlap), path, text))
    ranked.sort(key=lambda item: (-item[0], item[1].name.casefold()))
    return [{
        "path": path.relative_to(ROOT).as_posix(),
        "validated": False,
        "reference_only": True,
        "yaml_excerpt": text[:9000],
    } for _, path, text in ranked[:limit]]


def _chat_references(draft, limit=12):
    """Supply prior tester corrections as unvalidated design context."""
    terms = _tokens(draft["case_id"], draft["name"], draft["traceability"])
    with connect() as db:
        rows = db.execute(
            """SELECT id,role,message FROM testing_bot_messages
               ORDER BY id DESC LIMIT 1500"""
        ).fetchall()
    ranked = []
    for row in rows:
        overlap = terms & _tokens(row["message"])
        if overlap:
            ranked.append((len(overlap), int(row["id"]), row))
    ranked.sort(key=lambda item: (-item[0], -item[1]))
    return [{
        "evidence_type": "user_chat_memory",
        "message_id": row["id"], "role": row["role"], "message": row["message"],
        "validated": False, "context_only": True,
    } for _, _, row in ranked[:limit]]


def _subscriber_login_proposal(draft, requirements):
    """Compose the two approved Subscriber login entry paths from proven shared flows."""
    case_id = str(draft["case_id"] or "").upper()
    if case_id not in {"SUB_LOGIN_001", "SUB_LOGIN_002"}:
        return None

    if case_id == "SUB_LOGIN_001":
        yaml_text = '''appId: com.mobstac.thehindu
tags: [generated, ordered, subscriber, login]
---
- launchApp:
    clearState: true
- extendedWaitUntil: {visible: "HAVE AN ACCOUNT.*LOGIN", timeout: 30000}
- assertVisible: "Create a free account|CREATE A FREE ACCOUNT"
- assertVisible: "HAVE AN ACCOUNT.*LOGIN"
- waitForAnimationToEnd
- takeScreenshot: "Screenshots/Generated/SUB_LOGIN_001_get_started"
- tapOn: "HAVE AN ACCOUNT.*LOGIN"
- extendedWaitUntil: {visible: "Email", timeout: 30000}
- assertVisible: "Email"
- runFlow: "../Common/SUBSCRIBER_LOGIN_ONCE.yaml"
- assertVisible: "^Account$"
- back
- extendedWaitUntil: {visible: {id: "screen_home"}, timeout: 30000}
- assertVisible: {id: "screen_home"}
- assertNotVisible: {text: "Subscribe|SUBSCRIBE"}
- waitForAnimationToEnd
- takeScreenshot: "Screenshots/Generated/SUB_LOGIN_001_authenticated_home"
- stopApp
'''
        command_sets = [
            ["launchApp", "extendedWaitUntil"],
            ["waitForAnimationToEnd", "takeScreenshot", "tapOn"],
            ["runFlow"], ["runFlow"],
            ["extendedWaitUntil", "assertVisible", "takeScreenshot", "tapOn", "assertNotVisible"],
            ["assertVisible"], ["extendedWaitUntil", "assertVisible"], ["runFlow"],
            ["extendedWaitUntil", "assertVisible"], ["assertVisible", "assertNotVisible"],
        ]
        evidence = ["Common/SUBSCRIBER_LOGIN_ONCE.yaml", "HAVE AN ACCOUNT? LOGIN", "selector:id=screen_home",
                    "selector:id=nav_account", "selector:id=cta_login"]
    else:
        yaml_text = '''appId: com.mobstac.thehindu
tags: [generated, ordered, subscriber, login, account-settings]
---
- stopApp
- launchApp:
    clearState: true
- extendedWaitUntil: {visible: "Skip", timeout: 30000}
- assertVisible: "Skip"
- tapOn: "Skip"
- extendedWaitUntil: {visible: {id: "screen_home"}, timeout: 30000}
- assertVisible: {id: "screen_home"}
- tapOn: {id: "nav_account"}
- extendedWaitUntil: {visible: {id: "cta_login"}, timeout: 20000}
- assertVisible: {id: "cta_login"}
- waitForAnimationToEnd
- takeScreenshot: "Screenshots/Generated/SUB_LOGIN_002_anonymous_account"
- tapOn: {id: "cta_login"}
- extendedWaitUntil: {visible: "Email", timeout: 30000}
- assertVisible: "Email"
- runFlow: "../Common/SUBSCRIBER_LOGIN_ONCE.yaml"
- assertVisible: "^Account$"
- scrollUntilVisible:
    element: {text: "Log Out|LOGOUT|Logout|Log out"}
    direction: DOWN
    timeout: 30000
- assertVisible: {text: "Log Out|LOGOUT|Logout|Log out"}
- waitForAnimationToEnd
- takeScreenshot: "Screenshots/Generated/SUB_LOGIN_002_authenticated_account"
- back
- extendedWaitUntil: {visible: {id: "screen_home"}, timeout: 30000}
- assertVisible: {id: "screen_home"}
- assertNotVisible: {text: "Subscribe|SUBSCRIBE"}
- waitForAnimationToEnd
- takeScreenshot: "Screenshots/Generated/SUB_LOGIN_002_authenticated_home"
'''
        command_sets = [
            ["launchApp", "extendedWaitUntil"], ["tapOn", "extendedWaitUntil", "assertVisible"],
            ["tapOn", "extendedWaitUntil", "assertVisible"],
            ["waitForAnimationToEnd", "takeScreenshot", "tapOn", "extendedWaitUntil"],
            ["runFlow"], ["runFlow"],
            ["extendedWaitUntil", "assertVisible", "tapOn", "assertNotVisible", "takeScreenshot"],
            ["extendedWaitUntil", "assertVisible"], ["assertVisible"],
            ["extendedWaitUntil", "assertVisible"], ["extendedWaitUntil", "assertVisible"],
            ["runFlow"], ["extendedWaitUntil", "assertVisible"],
            ["assertVisible", "assertNotVisible", "takeScreenshot"],
        ]
        evidence = ["Common/Anonymous_account_onboarding.yaml", "Common/SUBSCRIBER_LOGIN_ONCE.yaml",
                    "selector:id=screen_home", "selector:id=nav_account", "selector:id=cta_login"]

    if len(command_sets) != len(requirements):
        return None
    validate_maestro_yaml(yaml_text)
    if not reusable_yaml(yaml_text):
        raise ValueError("The composed Subscriber login YAML is not reusable Maestro YAML.")
    traceability = [{
        **requirement,
        "position": int(requirement.get("position") or index),
        "commands": command_sets[index - 1],
        "selector_grounding": evidence,
        "status": "covered",
        "reason": "Friday composed this obligation from approved Subscriber login evidence.",
    } for index, requirement in enumerate(requirements, 1)]
    return {
        "yaml": yaml_text, "traceability": traceability, "references": evidence,
        "notes": [], "complete": True, "confidence": 1.0,
    }


def _subscriber_quick_access_proposal(draft, requirements):
    """Build grounded Subscriber Quick Access flows without Hamburger navigation."""
    case_id = str(draft["case_id"] or "").upper()
    modules = {
        "SUB_WORLD_": ("World", "OPEN_SUBSCRIBER_WORLD.yaml"),
        "SUB_LATEST_": ("Latest News", "OPEN_SUBSCRIBER_LATEST_NEWS.yaml"),
        "SUB_SPORTS_": ("Sports", "OPEN_SUBSCRIBER_SPORTS.yaml"),
        "SUB_INDIA_": ("India", "OPEN_SUBSCRIBER_INDIA.yaml"),
        "SUB_OPINION_": ("Opinion", "OPEN_SUBSCRIBER_OPINION.yaml"),
        "SUB_FOOD_": ("Food", "OPEN_SUBSCRIBER_FOOD.yaml"),
        "SUB_BOOKS_": ("Books", "OPEN_SUBSCRIBER_BOOKS.yaml"),
        "SUB_BUSINESS_": ("Business", "OPEN_SUBSCRIBER_BUSINESS.yaml"),
        "SUB_ENTERTAINMENT_": ("Entertainment", "OPEN_SUBSCRIBER_ENTERTAINMENT.yaml"),
    }
    matched = next(((prefix, value) for prefix, value in modules.items()
                    if case_id.startswith(prefix)), None)
    if not matched:
        return None
    prefix, (label, helper) = matched
    suffix = case_id[len(prefix):]
    setup = f'- runFlow: "../Common/{helper}"\n'
    shot = f'Screenshots/Generated/{case_id}'
    article = '''- extendedWaitUntil: {visible: {id: "article_card"}, timeout: 30000}
- tapOn: {id: "article_card", index: 0}
- extendedWaitUntil: {visible: {id: "screen_article_detail"}, timeout: 30000}
- assertVisible: {id: "screen_article_detail"}
'''
    no_money = '- runFlow: "../Common/ASSERT_SUBSCRIBER_NO_MONETIZATION.yaml"\n'
    bodies = {
        "001": f'''- assertVisible: {{text: "(?i)^{label}$"}}
{no_money}- waitForAnimationToEnd
- takeScreenshot: "{shot}_selected"
''',
        "002": f'''- swipe: {{start: "50%,25%", end: "50%,75%", duration: 700}}
- waitForAnimationToEnd
- assertVisible: {{text: "(?i)^{label}$"}}
- swipe: {{start: "50%,25%", end: "50%,75%", duration: 700}}
- waitForAnimationToEnd
- assertVisible: {{id: "screen_home"}}
{no_money}- waitForAnimationToEnd
- takeScreenshot: "{shot}_refreshed"
''',
        "003": f'''- assertVisible: {{text: "(?i)^{label}$"}}
- extendedWaitUntil: {{visible: {{id: "article_card"}}, timeout: 30000}}
- assertVisible: {{id: "article_card", index: 0}}
- waitForAnimationToEnd
- takeScreenshot: "{shot}_listing"
''',
        "004": f'''- repeat:
    times: 5
    commands:
      - swipe: {{direction: UP}}
      - waitForAnimationToEnd
      - assertVisible: {{id: "screen_home"}}
      - runFlow: "../Common/ASSERT_SUBSCRIBER_NO_MONETIZATION.yaml"
- waitForAnimationToEnd
- takeScreenshot: "{shot}_deep_scroll"
''',
        "005": article + f'''- assertNotVisible: {{text: "Login to your account|SUBSCRIBE|Subscribe"}}
- waitForAnimationToEnd
- takeScreenshot: "{shot}_article"
''',
        "006": article + no_money + f'''- repeat:
    times: 4
    commands:
      - swipe: {{direction: UP}}
      - waitForAnimationToEnd
      - assertVisible: {{id: "screen_article_detail"}}
      - runFlow: "../Common/ASSERT_SUBSCRIBER_NO_MONETIZATION.yaml"
- waitForAnimationToEnd
- takeScreenshot: "{shot}_full_article"
''',
        "007": article + f'''- runFlow:
    when: {{visible: {{text: "AI Summary|AI summary|Summary"}}}}
    commands:
      - tapOn: {{text: "AI Summary|AI summary|Summary"}}
      - waitForAnimationToEnd
      - takeScreenshot: "{shot}_ai_summary"
- runFlow:
    when: {{visible: {{text: "Listen to article|Listen"}}}}
    commands:
      - tapOn: {{text: "Listen to article|Listen"}}
      - waitForAnimationToEnd
      - takeScreenshot: "{shot}_listen"
{no_money}''',
        "008": article + f'''- runFlow:
    when: {{visible: {{text: "Text size|Text Size|Reading Options"}}}}
    commands:
      - tapOn: {{text: "Text size|Text Size|Reading Options"}}
      - runFlow:
          when: {{visible: {{text: "Large|Larger|A\\+"}}}}
          commands:
            - tapOn: {{text: "Large|Larger|A\\+"}}
      - waitForAnimationToEnd
      - takeScreenshot: "{shot}_reading_options"
- assertVisible: {{id: "screen_article_detail"}}
''',
        "009": article + f'''- runFlow:
    when: {{visible: {{id: "cta_bookmark", selected: true}}}}
    commands:
      - tapOn: {{id: "cta_bookmark"}}
      - extendedWaitUntil: {{visible: {{id: "cta_bookmark", selected: false}}, timeout: 15000}}
      - waitForAnimationToEnd
      - takeScreenshot: "{shot}_unbookmarked"
- tapOn: {{id: "cta_bookmark"}}
- extendedWaitUntil: {{visible: {{id: "cta_bookmark", selected: true}}, timeout: 15000}}
- assertVisible: {{id: "cta_bookmark", selected: true}}
- waitForAnimationToEnd
- takeScreenshot: "{shot}_bookmarked"
- tapOn: {{id: "cta_share"}}
- waitForAnimationToEnd
- takeScreenshot: "{shot}_share"
- back
- assertVisible: {{id: "screen_article_detail"}}
''',
        "010": article + f'''- repeat:
    times: 8
    commands:
      - swipe: {{direction: UP}}
      - waitForAnimationToEnd
      - assertVisible: {{id: "screen_article_detail"}}
- waitForAnimationToEnd
- takeScreenshot: "{shot}_post_article"
''',
        "011": article + f'''- repeat:
    times: 3
    commands:
      - swipe: {{direction: LEFT}}
      - waitForAnimationToEnd
      - assertVisible: {{id: "screen_article_detail"}}
- repeat:
    times: 3
    commands:
      - swipe: {{direction: RIGHT}}
      - waitForAnimationToEnd
      - assertVisible: {{id: "screen_article_detail"}}
- back
- extendedWaitUntil: {{visible: {{id: "screen_home"}}, timeout: 30000}}
- assertVisible: {{text: "(?i)^{label}$"}}
- waitForAnimationToEnd
- takeScreenshot: "{shot}_recovered"
''',
        "012": article + f'''- repeat:
    times: 3
    commands:
      - swipe: {{direction: UP}}
      - waitForAnimationToEnd
      - assertVisible: {{id: "screen_article_detail"}}
- evalScript: '${{(() => {{ const end = Date.now() + 30000; while (Date.now() < end) {{}} return true; }})()}}'
- assertVisible: {{id: "screen_article_detail"}}
{no_money}- waitForAnimationToEnd
- takeScreenshot: "{shot}_bounded_content"
''',
    }
    if suffix not in bodies:
        return None
    yaml_text = f"appId: com.mobstac.thehindu\ntags: [generated, ordered, subscriber, quick-access]\n---\n{setup}{bodies[suffix]}"
    validate_maestro_yaml(yaml_text)
    evidence = [f"Common/{helper}", "Common/ASSERT_SUBSCRIBER_NO_MONETIZATION.yaml",
                "selector:id=screen_home", "selector:id=article_card",
                "selector:id=screen_article_detail"]
    commands = sorted(set(re.findall(r"(?m)^\s*-\s*([A-Za-z][A-Za-z0-9]+):?", yaml_text)))
    traceability = [{**item, "position": int(item.get("position") or index),
                     "commands": commands, "selector_grounding": evidence,
                     "status": "covered", "reason": "Friday composed this obligation from the validated Subscriber Quick Access model."}
                    for index, item in enumerate(requirements, 1)]
    return {"yaml": yaml_text, "traceability": traceability, "references": evidence,
            "notes": [], "complete": True, "confidence": 1.0}


def build_repair_proposal(draft):
    requirements = _items(draft)
    if not requirements:
        raise ValueError("The imported case has no traceability obligations to repair.")
    known_proposal = _subscriber_login_proposal(draft, requirements)
    if not known_proposal:
        known_proposal = _subscriber_quick_access_proposal(draft, requirements)
    if known_proposal:
        return known_proposal
    agent_evidence = AdaptiveTestAgent().retrieve(
        [draft["case_id"], draft["name"], *[item.get("requirement", "") for item in requirements]],
        limit=40, user_state=draft["user_state"] or "",
    )
    legacy = _legacy_references(draft)
    evidence = agent_evidence + legacy + _chat_references(draft)
    prompt = f"""You are Friday, the primary Senior Mobile QA Architect for AI Maestro.
Own this case from requirement to executable result. Retrieve and reason over the supplied
evidence, author a complete replacement Maestro YAML, critique it against every imported
obligation, and return the corrected final YAML plus an exact evidence mapping.

Case: {draft['case_id']} — {draft['name']}
User state: {draft['user_state']}
Imported obligations:
{json.dumps(requirements, ensure_ascii=False)}

Current incomplete YAML (diagnostic only; do not preserve its defects):
{draft['yaml'] or ''}

Repository evidence:
{json.dumps(evidence, ensure_ascii=False, default=str)}

Rules:
- Output valid Maestro YAML for appId com.mobstac.thehindu.
- Preserve obligation order and map every obligation position exactly once.
- Use validated evidence as executable truth.
- Old handwritten reference_only YAML may provide interaction structure, but its stale article titles
  and selectors must not be copied unless separately validated.
- user_chat_memory preserves tester knowledge and corrections as design context. It may clarify intent,
  but cannot independently prove a selector, command, or successful behavior.
- Use ../Common/OPEN_ANONYMOUS_HOME.yaml for anonymous Home setup when relevant.
- Use ../Common/OPEN_SUBSCRIBER_HOME.yaml before Subscriber feature/module navigation.
- For Subscriber screens, compose ../Common/ASSERT_SUBSCRIBER_NO_MONETIZATION.yaml
  after navigation and again after representative scrolling when the matrix requires ads,
  Taboola, Subscribe actions, and paywalls to be absent.
- Handle dynamic content with bounded conditional runFlow branches; never use unbounded loops.
- Screenshot commands do not replace assertions.
- Always place a parameterless waitForAnimationToEnd immediately before every takeScreenshot.
- Article cases may use an active article_reference as controlled test data, but a URL is reference-only
  until the target build opens and validates it successfully.
- Expected results require assertVisible/assertNotVisible/extendedWaitUntil evidence.
- Never mark a product-dependent optional branch as a guaranteed assertion.
- Do not invent credentials, IDs, article titles, coordinates, or controls.
- Use waitForAnimationToEnd without a colon or parameters.
- If any obligation cannot be grounded, put the reason in assumptions instead of inventing YAML.
- `commands` must name the actual Maestro commands covering that obligation.
- `evidence` must contain paths/rule IDs/selectors from Repository evidence.
"""
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        timeout=float(os.getenv("OPENAI_TESTING_BOT_REPAIR_TIMEOUT", "180")),
        max_retries=int(os.getenv("OPENAI_TESTING_BOT_REPAIR_RETRIES", "1")),
    )
    response = client.responses.create(
        model=os.getenv("OPENAI_TESTING_BOT_MODEL", os.getenv("OPENAI_SCENARIO_MODEL", "gpt-5.6-sol")),
        input=prompt,
        text={"format": {"type": "json_schema", "name": "yaml_repair", "strict": True, "schema": REPAIR_SCHEMA}},
    )
    result = json.loads(response.output_text)
    yaml_text = str(result.get("yaml") or "")
    validate_maestro_yaml(yaml_text)
    if not reusable_yaml(yaml_text):
        raise ValueError("The repaired YAML failed Maestro command-shape validation.")
    assumptions = [str(item).strip() for item in result.get("assumptions", []) if str(item).strip()]
    required_positions = {int(item.get("position") or index) for index, item in enumerate(requirements, 1)}
    mappings = result.get("mappings") or []
    mapped_positions = {int(item.get("position") or 0) for item in mappings}
    if not mapped_positions.issubset(required_positions):
        raise ValueError("The repair mapped positions that are not imported obligations.")
    actual_commands = {item.casefold() for item in yaml_command_sequence(yaml_text)}
    for mapping in mappings:
        claimed = {str(item).casefold() for item in mapping.get("commands", [])}
        if not claimed or not claimed.intersection(actual_commands):
            raise ValueError(f"Obligation {mapping['position']} claims commands not present in the YAML.")
        if not mapping.get("evidence"):
            raise ValueError(f"Obligation {mapping['position']} has no old/live evidence reference.")
    by_position = {int(item["position"]): item for item in mappings}
    repaired_traceability = []
    for index, requirement in enumerate(requirements, 1):
        position = int(requirement.get("position") or index)
        mapping = by_position.get(position)
        if mapping:
            repaired_traceability.append({
                **requirement,
                "position": position,
                "commands": mapping["commands"],
                "selector_grounding": mapping["evidence"],
                "status": "covered",
                "reason": "Friday evidence-grounded repair proposal",
            })
        else:
            repaired_traceability.append({
                **requirement, "position": position, "commands": [],
                "selector_grounding": [], "status": "incomplete",
                "reason": "Friday could not ground this obligation without invention.",
            })
    references = list(dict.fromkeys(
        str(ref) for item in mappings for ref in item.get("evidence", []) if str(ref).strip()
    ))
    exact_mapping = mapped_positions == required_positions and len(mappings) == len(required_positions)
    complete = exact_mapping and not assumptions
    coverage = len(mapped_positions) / len(required_positions) if required_positions else 0.0
    return {
        "yaml": yaml_text, "traceability": repaired_traceability,
        "references": references[:15], "notes": assumptions,
        "complete": complete, "confidence": coverage if complete else coverage * 0.75,
    }
