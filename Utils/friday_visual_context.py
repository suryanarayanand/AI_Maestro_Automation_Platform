"""Build conservative Friday context for screenshot-level AI review."""

from __future__ import annotations

import json
import re

from web.portal_db import connect


GENERIC_TOKENS = {
    "account", "all", "and", "android", "app", "application", "available", "behavior",
    "case", "content", "displayed", "expected", "feature", "hidden", "not",
    "or", "page", "result", "screen", "state", "subscriber", "test", "testing",
    "user", "users", "visible", "yaml", "article",
}


def _tokens(values):
    text = " ".join(str(value or "") for value in values).casefold()
    return {
        token for token in re.findall(r"[a-z0-9_]+", text)
        if len(token) > 2 and token not in GENERIC_TOKENS
    }


def _json_list(value):
    try:
        parsed = json.loads(value or "[]")
        return parsed if isinstance(parsed, list) else []
    except (TypeError, ValueError, json.JSONDecodeError):
        return []


def build_friday_visual_context(case_id, screenshot_name=""):
    """Return approved case expectations without exposing noisy draft internals."""
    with connect() as database:
        draft = database.execute(
            """SELECT case_id,name,source_file,user_state,traceability
               FROM drafts WHERE case_id=? ORDER BY id DESC LIMIT 1""",
            (case_id,),
        ).fetchone()
        rule_rows = database.execute(
            """SELECT rule_id,intent,trigger_terms,expected_behavior,yaml_guidance
               FROM app_behavior_rules WHERE status='approved'
               AND (user_state=? OR user_state='ALL')""",
            (draft["user_state"] if draft else "",),
        ).fetchall()

    if not draft:
        return {
            "case_id": case_id,
            "screenshot_checkpoint": screenshot_name,
            "evidence_status": "No approved case/Excel context found; use visual evidence only.",
            "requirements": [],
            "approved_behavior_rules": [],
        }

    traceability = _json_list(draft["traceability"])
    requirements = []
    for item in traceability:
        requirement = str(item.get("requirement") or "").strip()
        if requirement and requirement not in requirements:
            requirements.append(requirement)

    primary_tokens = _tokens([draft["name"], screenshot_name])
    requirement_tokens = _tokens(requirements)
    ranked_rules = []
    for row in rule_rows:
        intent_tokens = _tokens([row["intent"]])
        rule_tokens = _tokens([
            row["intent"], row["trigger_terms"], row["expected_behavior"],
        ])
        primary_overlap = primary_tokens & intent_tokens
        if primary_overlap:
            score = (len(primary_overlap) * 3) + len(requirement_tokens & rule_tokens)
            ranked_rules.append((score, row["rule_id"], row))
    ranked_rules.sort(key=lambda item: (-item[0], item[1]))
    rules = [{
        "rule_id": row["rule_id"],
        "intent": row["intent"],
        "expected_behavior": row["expected_behavior"],
        "yaml_guidance": row["yaml_guidance"],
    } for _, _, row in ranked_rules[:8]]

    return {
        "case_id": case_id,
        "case_name": draft["name"],
        "user_state": draft["user_state"],
        "excel_source": draft["source_file"],
        "screenshot_checkpoint": screenshot_name,
        "requirements": requirements,
        "approved_behavior_rules": rules,
        "evidence_policy": (
            "Excel requirements and approved Friday rules define expected behavior. "
            "The screenshot proves only its visible instant; execution timing and selector "
            "failures are automation concerns."
        ),
    }
