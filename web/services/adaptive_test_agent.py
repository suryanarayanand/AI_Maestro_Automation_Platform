"""Conservative retrieval and learning policy for adaptive test generation."""

from __future__ import annotations

import json
import re
from pathlib import Path

from web.portal_db import connect


ROOT = Path(__file__).resolve().parents[2]


STOP_WORDS = {
    "a", "an", "and", "app", "application", "at", "button", "for", "from",
    "icon", "in", "is", "it", "of", "on", "page", "screen", "section", "that", "the",
    "then", "to", "using", "verify", "with",
}


def _tokens(values):
    text = " ".join(str(value or "") for value in values).casefold().replace("_", " ")
    tokens = {
        token for token in re.findall(r"[a-z0-9_]+", text)
        if len(token) > 1 and token not in STOP_WORDS
    }
    if "user icon" in text or "profile icon" in text:
        tokens.add("account")
    return tokens


def yaml_command_sequence(yaml_text):
    """Return the ordered Maestro command names from a reviewed/executed flow."""
    return re.findall(
        r"^\s*-\s+([A-Za-z][A-Za-z0-9]*)(?::|\s*$)",
        str(yaml_text or ""), re.MULTILINE,
    )


def reusable_yaml(yaml_text):
    """Reject known non-executable Maestro shapes before memory can reuse them."""
    text = str(yaml_text or "")
    if not text.strip() or "appId:" not in text or "---" not in text:
        return False
    # waitForAnimationToEnd is a parameterless Maestro command. A trailing colon
    # produces either null or a mapping and is rejected by Maestro at runtime.
    if re.search(r"^\s*-\s+waitForAnimationToEnd\s*:", text, re.MULTILINE):
        return False
    return bool(yaml_command_sequence(text))


def classify_execution_failure(log):
    """Separate the immediate Maestro error from the earlier workflow defect."""
    text = str(log or "")
    if re.search(r"Play Latest Episode.*COMPLETED", text, re.I | re.S) and re.search(
        r"Assert that .*Pause.* is visible.*FAILED", text, re.I | re.S
    ):
        return {
            "classification": "PRODUCT_BUG",
            "root_cause": (
                "The Podcast page accepted Play Latest Episode, but playback did not start "
                "and no Pause control appeared within the bounded 30-second wait."
            ),
            "component": "podcast_playback_loading",
        }
    if re.search(
        r"blank-loading product defect|podcast playback/mini-player product defect|"
        r"product-bug-on-(?:blank-loading|identity-or-loading)",
        text,
        re.I,
    ) and re.search(r"FAILED|Assertion is false|assertWithAI", text, re.I):
        return {
            "classification": "PRODUCT_BUG",
            "root_cause": (
                "The executable Podcast product assertion reproduced a persistent blank/loading "
                "series page or an incorrect/non-starting mini-player after its bounded wait."
            ),
            "component": "podcast_content_or_playback",
        }
    if "ExceptionInInitializerError" in text and re.search(
        r"Maestro\\Logs\\[^\r\n]+\\maestro\.log\.lck|maestro\.log\.lck", text, re.I
    ):
        return {
            "classification": "TEST_DATA_OR_ENVIRONMENT_ISSUE",
            "root_cause": (
                "Maestro failed during debug-log initialization because its timestamped "
                "log directory disappeared before maestro.log.lck could be created. "
                "No YAML command or application behavior was executed."
            ),
            "component": "maestro_debug_log_initialization",
        }
    if re.search(r"UNAVAILABLE|tcp:\d+\): closed|0 devices connected|Not enough devices connected", text, re.I):
        return {
            "classification": "TEST_DATA_OR_ENVIRONMENT_ISSUE",
            "root_cause": "The Android/Maestro transport or required device was unavailable.",
            "component": "device_transport",
        }
    if re.search(r"Element not found: Id matching regex: nav_home", text, re.I) and re.search(
        r"screen_section is visible\.\.\. COMPLETED", text, re.I
    ):
        return {
            "classification": "AUTOMATION_SCRIPT_ISSUE",
            "root_cause": (
                "The flow reached a nested section where nav_home was not exposed, then used "
                "nav_home instead of Back or a state-preserving relaunch."
            ),
            "component": "generated_navigation",
        }
    if re.search(r"screen_article_detail is visible\.\.\. FAILED", text, re.I) and len(
        re.findall(r"Swiping in UP direction.*COMPLETED", text, re.I)
    ) >= 1:
        return {
            "classification": "AUTOMATION_SCRIPT_ISSUE",
            "root_cause": (
                "The article assertion failed after scrolling; an asynchronous overlay or "
                "scroll-state hierarchy change must be handled before asserting article detail."
            ),
            "component": "generated_overlay_handling",
        }
    login_started = len(re.findall(r"^\s*Run \.\./Common/LOGIN\.yaml\.\.\.$", text, re.MULTILINE))
    login_completed = bool(re.search(
        r"^\s*Run \.\./Common/LOGIN\.yaml\.\.\. COMPLETED$", text, re.MULTILINE
    ))
    article_opened = bool(re.search(
        r'(?:Tap on "READ FULL ARTICLE"|Tap on .*article).*COMPLETED', text, re.IGNORECASE
    ))
    email_failure = '"Email" is visible... FAILED' in text or '"Email" is visible\' failed' in text
    if login_started >= 2 and login_completed and article_opened and email_failure:
        return {
            "classification": "generation_order_defect",
            "root_cause": (
                "LOGIN.yaml was invoked again after authentication completed and the article "
                "was opened; the Email assertion is only the immediate symptom."
            ),
            "component": "generated_scenario",
        }
    return {
        "classification": "execution_failure",
        "root_cause": "The available log does not prove an earlier workflow-order defect.",
        "component": "unknown",
    }


class AdaptiveTestAgent:
    """Retrieve evidence without promoting observations into executable truth."""

    def retrieve(self, steps, limit=30, user_state=""):
        query_tokens = _tokens(steps)
        if not query_tokens:
            return []
        requested_state = str(user_state or "").strip().upper().replace("-", "_").replace(" ", "_")
        if "ANONYMOUS" in requested_state:
            requested_state = "ANONYMOUS"
        elif "EXPIRED" in requested_state:
            requested_state = "EXPIRED_USER"
        elif "REGISTERED" in requested_state or "NON_SUBSCRIBER" in requested_state:
            requested_state = "REGISTERED_USER"
        elif "SUBSCRIB" in requested_state:
            requested_state = "SUBSCRIBER"
        with connect() as db:
            rules = db.execute(
                """SELECT * FROM app_behavior_rules WHERE status='approved'
                   AND (?='' OR user_state=? OR user_state='ALL')""",
                (requested_state, requested_state),
            ).fetchall()
        rule_ranked = []
        for row in rules:
            overlap = query_tokens & _tokens((
                row["intent"], row["trigger_terms"], row["expected_behavior"],
                row["yaml_guidance"],
            ))
            if overlap:
                rule_ranked.append((len(overlap), {
                    "evidence_type": "approved_behavior_rule",
                    "rule_id": row["rule_id"], "user_state": row["user_state"],
                    "intent": row["intent"],
                    "expected_behavior": row["expected_behavior"],
                    "yaml_guidance": row["yaml_guidance"],
                    "validated": True,
                }))
        rule_ranked.sort(key=lambda item: (-item[0], item[1]["rule_id"]))
        rule_items = [item for _, item in rule_ranked[:min(6, limit)]]
        with connect() as db:
            catalog_rows = db.execute(
                """SELECT case_id,scenario,source_text,user_state,module,tags,source_file,source_row
                   FROM atomic_flow_steps
                   WHERE source_file='TH App Testing Scenarios_AutomationCopy.xlsx'"""
            ).fetchall()
        catalog_ranked = []
        for row in catalog_rows:
            overlap = query_tokens & _tokens((
                row["scenario"], row["source_text"], row["module"], row["tags"]
            ))
            if not overlap:
                continue
            catalog_ranked.append((len(overlap), {
                "evidence_type": "master_scenario_reference",
                "case_id": row["case_id"], "scenario": row["scenario"],
                "requirement": row["source_text"], "user_state": row["user_state"],
                "module": row["module"], "source": row["source_file"],
                "source_row": row["source_row"], "validated": False,
                "reference_only": True,
            }))
        catalog_ranked.sort(key=lambda item: (-item[0], item[1]["source_row"] or 0))
        catalog_items = [item for _, item in catalog_ranked[:min(5, max(1, limit // 5))]]
        with connect() as db:
            article_rows = db.execute(
                """SELECT id,label,url,module,article_type,user_state,notes,source_file
                   FROM article_references WHERE active=1"""
            ).fetchall()
        article_ranked = []
        for row in article_rows:
            row_state = str(row["user_state"] or "ANY").upper()
            if requested_state and row_state not in {"ANY", requested_state}:
                continue
            overlap = query_tokens & _tokens((
                row["label"], row["module"], row["article_type"], row["notes"]
            ))
            if not overlap:
                continue
            article_ranked.append((len(overlap), {
                "evidence_type": "article_reference",
                "reference_id": row["id"], "label": row["label"], "url": row["url"],
                "module": row["module"], "article_type": row["article_type"],
                "user_state": row_state, "notes": row["notes"],
                "source": row["source_file"], "validated": False,
                "reference_only": True,
            }))
        article_ranked.sort(key=lambda item: (-item[0], item[1]["article_type"], item[1]["reference_id"]))
        article_items = [item for _, item in article_ranked[:min(6, max(1, limit // 4))]]
        with connect() as db:
            rows = db.execute(
                """SELECT s.name screen,e.name,e.locator_type,e.locator_value,
                          e.confidence,e.source,e.clickable
                   FROM app_memory_elements e
                   JOIN app_memory_screens s ON s.id=e.screen_id
                   WHERE e.confidence>=0.75"""
            ).fetchall()
        ranked = []
        for row in rows:
            element_overlap = query_tokens & _tokens((row["name"], row["locator_value"]))
            screen_overlap = query_tokens & _tokens((row["screen"],))
            validated = float(row["confidence"]) == 1.0
            # A screen-name match is broad. It may expose only reviewed evidence;
            # hierarchy observations must match the requested element itself.
            if not element_overlap and not (screen_overlap and validated):
                continue
            score = len(element_overlap) * 20 + len(screen_overlap) * 2 + float(row["confidence"])
            ranked.append((score, {
                "screen": row["screen"], "name": row["name"],
                "locator_type": row["locator_type"], "locator_value": row["locator_value"],
                "confidence": float(row["confidence"]), "source": row["source"],
                "validated": validated,
                "clickable": bool(row["clickable"]),
            }))
        ranked.sort(key=lambda item: (-item[0], item[1]["screen"], item[1]["name"]))
        # Behavior rules are authoritative. Catalog rows supply coverage ideas,
        # never selectors or state expectations, and therefore remain reference-only.
        unique = list(rule_items) + catalog_items + article_items
        seen = set()
        # Reserve part of the context budget for accepted execution/YAML lessons;
        # otherwise broad locator matches can crowd out all behavioral evidence.
        lesson_budget = min(8, max(1, limit // 3))
        flow_budget = min(5, max(1, limit // 4))
        locator_limit = max(0, limit - lesson_budget - flow_budget)
        for _, item in ranked:
            key = (item["screen"], item["locator_type"], item["locator_value"])
            if key not in seen:
                unique.append(item)
                seen.add(key)
            if len(unique) >= locator_limit:
                break
        remaining = max(0, limit - len(unique))
        if remaining:
            with connect() as db:
                lessons = db.execute(
                    """SELECT case_id,observation_type,payload,confidence,source,status
                       FROM app_memory_learning
                       WHERE status='accepted'
                          OR (status='pending' AND observation_type='execution_failure')
                       ORDER BY confidence DESC,id DESC LIMIT 200"""
                ).fetchall()
            lesson_ranked = []
            for row in lessons:
                try:
                    payload = json.loads(row["payload"] or "{}")
                except json.JSONDecodeError:
                    continue
                lesson_state = str(payload.get("user_state") or "").strip().upper()
                if requested_state and lesson_state and lesson_state != requested_state:
                    continue
                overlap = query_tokens & _tokens((
                    row["case_id"], payload.get("name"), payload.get("requirements"),
                    payload.get("completed_tail"), payload.get("command_sequence"),
                    payload.get("selector_decisions"),
                    payload.get("failed_step"), payload.get("error"),
                    payload.get("classification"), payload.get("root_cause"),
                ))
                if not overlap:
                    continue
                accepted = row["status"] == "accepted"
                lesson_ranked.append((len(overlap) * 10 + float(row["confidence"]), {
                    "evidence_type": "accepted_learning" if accepted else "negative_learning",
                    "observation_type": row["observation_type"],
                    "case_id": row["case_id"], "confidence": float(row["confidence"]),
                    "source": row["source"], "payload": payload,
                    "validated": accepted,
                }))
            lesson_ranked.sort(key=lambda item: -item[0])
            unique.extend(item for _, item in lesson_ranked[:min(remaining, lesson_budget)])
        remaining = max(0, limit - len(unique))
        if remaining:
            with connect() as db:
                flows = db.execute(
                    """SELECT path,command_sequence,search_text,tags,pass_count,fail_count
                       FROM app_memory_flows ORDER BY pass_count DESC,last_indexed_at DESC"""
                ).fetchall()
            ranked_flows = []
            for row in flows:
                overlap = query_tokens & _tokens((row["path"], row["search_text"], row["tags"]))
                if not overlap:
                    continue
                passed, failed = int(row["pass_count"]), int(row["fail_count"])
                flow_path = ROOT / row["path"]
                trusted_common = str(row["path"]).replace("\\", "/").startswith("Common/")
                # Common flows are curated reusable building blocks. Executed
                # scenarios are reusable only after a passing run. Failed and
                # unexecuted scenarios remain observations, never truth.
                reusable = trusted_common or passed > 0
                yaml_excerpt = ""
                if reusable and flow_path.is_file():
                    yaml_excerpt = flow_path.read_text(
                        encoding="utf-8-sig", errors="replace"
                    )[:12000]
                ranked_flows.append((len(overlap) * 10 + passed * 2 - failed + (3 if trusted_common else 0), {
                    "evidence_type": "trusted_common_flow" if trusted_common else (
                        "passed_repository_flow" if passed else "repository_flow_observation"
                    ),
                    "path": row["path"], "command_sequence": json.loads(row["command_sequence"] or "[]"),
                    "tags": json.loads(row["tags"] or "[]"), "pass_count": passed,
                    "fail_count": failed, "validated": reusable,
                    "yaml_excerpt": yaml_excerpt,
                }))
            ranked_flows.sort(key=lambda item: -item[0])
            unique.extend(item for _, item in ranked_flows[:min(remaining, flow_budget)])
        return unique

    @staticmethod
    def approved_yaml(case_id, user_state=""):
        """Return an exact, accepted YAML lesson only for the same case and state."""
        requested_state = str(user_state or "").strip().upper()
        with connect() as db:
            rows = db.execute(
                """SELECT payload FROM app_memory_learning
                   WHERE case_id=? AND observation_type IN ('approved_yaml','execution_success')
                         AND status='accepted'
                   ORDER BY id DESC""",
                (case_id,),
            ).fetchall()
        for row in rows:
            try:
                payload = json.loads(row["payload"] or "{}")
            except json.JSONDecodeError:
                continue
            lesson_state = str(payload.get("user_state") or "").strip().upper()
            if requested_state and lesson_state != requested_state:
                continue
            if payload.get("yaml") and reusable_yaml(payload["yaml"]):
                return payload
        return None

    @staticmethod
    def record_learning(observation_type, payload, source, confidence, case_id=None,
                        status="pending"):
        """Record a proposal; it cannot affect executable memory until reviewed."""
        with connect() as db:
            cursor = db.execute(
                """INSERT INTO app_memory_learning(
                   case_id,observation_type,payload,confidence,status,source)
                   VALUES(?,?,?,?, ?, ?)""",
                (case_id, observation_type, json.dumps(payload, ensure_ascii=False),
                 float(confidence), status, source),
            )
            return cursor.lastrowid

    @classmethod
    def learn_from_locator_grounding(cls, case_id, name, user_state, requirements,
                                     selector_decisions):
        """Store selector decisions as conservative child-agent memory."""
        decisions = [dict(item) for item in selector_decisions if item]
        accepted = [item for item in decisions if item.get("source") == "validated_repository"]
        pending = [item for item in decisions if item.get("source") != "validated_repository"]
        ids = []
        for status, items, confidence in (("accepted", accepted, 1.0), ("pending", pending, 0.6)):
            if not items:
                continue
            ids.append(cls.record_learning(
                "locator_grounding", {
                    "name": name, "user_state": user_state,
                    "requirements": list(requirements), "selector_decisions": items,
                }, source=f"yaml_generation:{case_id}:{status}", confidence=confidence,
                case_id=case_id, status=status,
            ))
        return ids

    @classmethod
    def learn_from_execution(cls, case_id, status, stdout="", stderr="", source="execution",
                             yaml_text="", name="", user_state="", failure_plan=None):
        """Store compact pass/failure evidence without mutating validated memory."""
        log = str(stderr or stdout or "")
        lines = [line.strip() for line in log.splitlines() if line.strip()]
        failed = next((line for line in reversed(lines) if "FAILED" in line), "")
        error = next((line for line in lines if line.startswith((
            "Assertion is false:", "Element not found:", "No visible element found:",
            "Element with ", "Could not find",
        ))), "")
        completed = [line for line in lines if "COMPLETED" in line][-20:]
        observation_type = "execution_success" if str(status).upper() == "PASS" else "execution_failure"
        payload = {
            "status": str(status).upper(), "failed_step": failed,
            "error": error, "completed_tail": completed, "name": name,
            "user_state": user_state, "command_sequence": yaml_command_sequence(yaml_text),
            "yaml_hash": __import__("hashlib").sha256(
                str(yaml_text or "").encode("utf-8")
            ).hexdigest() if yaml_text else "",
            "yaml": str(yaml_text) if observation_type == "execution_success" else "",
        }
        if observation_type == "execution_failure":
            payload.update(classify_execution_failure(log))
            if failure_plan:
                payload["video_failure_plan"] = failure_plan
        learned_status = (
            "accepted" if observation_type == "execution_success" and reusable_yaml(yaml_text)
            else "pending"
        )
        with connect() as db:
            existing = db.execute(
                """SELECT id FROM app_memory_learning
                   WHERE case_id=? AND observation_type=? AND source=?""",
                (case_id, observation_type, source),
            ).fetchone()
        if existing:
            with connect() as db:
                db.execute(
                    """UPDATE app_memory_learning SET payload=?,confidence=?,status=?
                       WHERE id=?""",
                    (json.dumps(payload, ensure_ascii=False),
                     0.95 if observation_type == "execution_success" else 0.85,
                     learned_status, existing["id"]),
                )
            return existing["id"]
        return cls.record_learning(
            observation_type, payload, source,
            confidence=0.95 if observation_type == "execution_success" else 0.85,
            case_id=case_id,
            # A passing execution is executable evidence. Failures remain proposals
            # until a reviewer accepts the diagnosed lesson.
            status=learned_status,
        )

    @classmethod
    def learn_from_approved_yaml(cls, case_id, name, yaml_text, user_state, reviewer):
        """Store a human-reviewed YAML structure as an accepted generation example."""
        payload = {
            "name": name, "user_state": user_state,
            "command_sequence": yaml_command_sequence(yaml_text),
            "yaml": str(yaml_text), "reviewer": reviewer,
        }
        return cls.record_learning(
            "approved_yaml", payload, source=f"approved:{case_id}", confidence=1.0,
            case_id=case_id, status="accepted",
        )
