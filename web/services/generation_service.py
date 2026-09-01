import json
import os
import re
import sys
import threading
from types import SimpleNamespace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GENERATION = ROOT / "generation"
if str(GENERATION) not in sys.path:
    sys.path.insert(0, str(GENERATION))

from excel_reader import ExcelReader
from yaml_generator import YAMLGenerator
from convert_to_supported_excel import convert as convert_to_supported_excel
from web.portal_db import connect
from web.services.adaptive_test_agent import AdaptiveTestAgent
from web.services.app_memory_service import index_yaml_flows
from web.services.testing_bot_repair_service import build_repair_proposal


MIN_APPROVAL_COVERAGE = 0.50
DEFAULT_GENERATION_CASES = 10
MAX_AI_FALLBACKS_PER_CASE = max(0, int(os.getenv("MAX_AI_FALLBACKS_PER_CASE", "1")))
AUTO_REPAIR_PENDING_YAML = os.getenv("AUTO_REPAIR_PENDING_YAML", "1").strip().casefold() not in {
    "0", "false", "no", "off",
}


def _auto_repair_pending_draft(draft_id):
    """Complete an incomplete pending draft only when every obligation is grounded."""
    if not AUTO_REPAIR_PENDING_YAML or not os.getenv("OPENAI_API_KEY"):
        return False
    with connect() as db:
        draft = db.execute("SELECT * FROM drafts WHERE id=? AND status='pending'", (draft_id,)).fetchone()
    if not draft or draft["coverage_status"] == "complete":
        return False
    with connect() as db:
        db.execute(
            "UPDATE drafts SET generation_mode='friday-reviewing',error=NULL WHERE id=?",
            (draft_id,),
        )
    try:
        repaired = build_repair_proposal(draft)
    except Exception as exc:
        with connect() as db:
            db.execute(
                "UPDATE drafts SET ai_assumptions=?,generation_mode='auto-repair-blocked' WHERE id=?",
                (json.dumps([str(exc)], ensure_ascii=False), draft_id),
            )
        return False
    with connect() as db:
        complete = bool(repaired.get("complete"))
        db.execute(
            """UPDATE drafts SET yaml=?,error=NULL,generation_mode=?,
               ai_confidence=?,ai_assumptions=?,traceability=?,coverage_status=?
               WHERE id=? AND status='pending'""",
            (repaired["yaml"], "friday-auto-repair" if complete else "friday-partial",
             float(repaired.get("confidence", 0)),
             json.dumps(repaired.get("notes", []), ensure_ascii=False),
             json.dumps(repaired["traceability"], ensure_ascii=False),
             "complete" if complete else "incomplete", draft_id),
        )
    return True


def _friday_repair_batch(draft_ids):
    """Let Friday finish drafts without holding the browser upload request open."""
    for draft_id in draft_ids:
        _auto_repair_pending_draft(draft_id)


def start_friday_repair(draft_ids):
    """Start one bounded background reviewer for a newly imported workbook."""
    if not draft_ids or not AUTO_REPAIR_PENDING_YAML or not os.getenv("OPENAI_API_KEY"):
        return False
    worker = threading.Thread(
        target=_friday_repair_batch,
        args=(tuple(draft_ids),),
        name=f"friday-yaml-review-{draft_ids[0]}",
        daemon=True,
    )
    worker.start()
    return True


def resume_friday_reviews():
    """Resume interrupted background reviews after a portal restart."""
    with connect() as db:
        db.execute(
            """UPDATE drafts SET generation_mode='friday-queued'
               WHERE status='pending' AND coverage_status='incomplete'
                 AND generation_mode='friday-reviewing'"""
        )
        rows = db.execute(
            """SELECT id FROM drafts
               WHERE status='pending' AND coverage_status='incomplete'
                 AND generation_mode IN ('rules','auto-repair-blocked',
                                         'friday-queued','friday-partial')
               ORDER BY id"""
        ).fetchall()
    return start_friday_repair([int(row["id"]) for row in rows])


def generation_case_limit():
    """Use the case-count value saved in Settings for workbook intake too."""
    with connect() as db:
        row = db.execute(
            "SELECT value FROM portal_settings WHERE key='execution_batch_size'"
        ).fetchone()
    try:
        return max(1, min(100, int(row["value"]))) if row else DEFAULT_GENERATION_CASES
    except (TypeError, ValueError):
        return DEFAULT_GENERATION_CASES
SCENARIO_LOCKS = ROOT / "Scenarios" / "locked_scenarios.json"


def traceability_coverage(traceability):
    """Return the covered requirement ratio; missing traceability is zero."""
    if isinstance(traceability, str):
        try:
            traceability = json.loads(traceability or "[]")
        except json.JSONDecodeError:
            return 0.0
    if not traceability:
        return 0.0
    return sum(item.get("status") == "covered" for item in traceability) / len(traceability)


def _prepared_steps(case):
    """Prefer visible text when Excel describes a labeled button assertion."""
    derived, covered_labels = [], set()
    kept_steps = []
    pattern = re.compile(
        r"(?:verify\s+)?(?:the\s+)?(.+?)\s+button\s+(?:must|should)\s+not\s+be\s+visible",
        re.IGNORECASE,
    )
    for step in case.get("steps", []):
        match = pattern.search(str(step))
        if match:
            label = match.group(1).strip().title()
            covered_labels.add(label.casefold())
            # Keep the derived assertion at the same source-row position.
            kept_steps.append(f"ASSERT_NOT_VISIBLE_TEXT({label})")
        else:
            kept_steps.append(step)
    for expected in case.get("expected_results", []):
        for line in str(expected).splitlines():
            match = pattern.search(line)
            if match:
                label = match.group(1).strip().title()
                if label.casefold() not in covered_labels:
                    covered_labels.add(label.casefold())
                    derived.append(f"ASSERT_NOT_VISIBLE_TEXT({label})")
    intents = []
    for intent in case.get("automation_intents", []):
        target = re.search(r"ASSERT_NOT_VISIBLE\(([^)]+)\)", str(intent), re.IGNORECASE)
        normalized = re.sub(r"^(?:cta|btn|button)_", "", target.group(1), flags=re.IGNORECASE) if target else ""
        if normalized.casefold() in covered_labels:
            continue
        intents.append(intent)
    return kept_steps + intents + derived


def _requirement_input(requirement):
    """Prefer explicit, reviewer-supplied automation data over inferred prose."""
    if requirement.get("automation_intent"):
        return requirement["automation_intent"]
    expected = str(requirement.get("expected_result") or "").strip()
    element = str(requirement.get("element_id") or "").strip()
    negative = re.search(r"\b(?:not|never|absent|missing|does not|mustn't|shouldn't)\b", expected, re.I)
    labeled = re.search(r"(?:the\s+)?(.+?)\s+button\s+(?:must|should|is|does)\b", expected, re.I)
    if expected and negative and labeled and not element:
        return f"ASSERT_NOT_VISIBLE_TEXT({labeled.group(1).strip().title()})"
    if expected and element:
        # The app exposes the ad marker as visible text. Excel sometimes places
        # that value in the Element ID column, but generating id: ADVERTISEMENT
        # creates a selector that cannot exist in the hierarchy.
        if element.strip().upper() == "ADVERTISEMENT":
            action = "ASSERT_NOT_VISIBLE_TEXT" if negative else "ASSERT_VISIBLE_TEXT"
            return f"{action}(ADVERTISEMENT)"
        return f"{'ASSERT_NOT_VISIBLE' if negative else 'ASSERT_VISIBLE'}({element})"
    return expected


def _generation_items(case):
    items = [{"source_type": "step", "text": step,
              "required_assertion": bool(re.match(r"\s*(?:verify|assert|validate|check)\b", str(step), re.I))}
             for step in _prepared_steps({**case, "expected_results": [], "automation_intents": []})]
    for requirement in case.get("requirements", []):
        # A yaml_command belongs to the same source row as `step`; it is a
        # reviewer/reference mapping, not an additional execution obligation.
        # Generating from both fields duplicated simple flows and converted
        # prose such as "button is tapped" into false visibility assertions.
        if requirement.get("yaml_command"):
            continue
        text = _requirement_input(requirement)
        if not text:
            continue
        items.append({
            "source_type": "expected_result", "text": text, "required_assertion": True,
            "expected_result": requirement.get("expected_result") or text,
            "step_number": requirement.get("step_number"),
            "source_sheet": requirement.get("source_sheet", ""),
            "source_row": requirement.get("source_row"),
            "element_id": requirement.get("element_id", ""),
        })
    # Support older canonical workbooks which have case-level intent/expected fields.
    if not case.get("requirements"):
        for text in case.get("automation_intents", []) + case.get("expected_results", []):
            items.append({"source_type": "expected_result", "text": text,
                          "expected_result": text, "required_assertion": True})
    return items


def _actions(steps):
    actions = []
    def visit(value):
        if isinstance(value, dict):
            if value.get("command"):
                actions.append(str(value["command"]))
            for key in value:
                if key in {"assertVisible", "assertNotVisible", "extendedWaitUntil",
                           "tapOn", "takeScreenshot", "swipe", "back", "runFlow"}:
                    actions.append(key)
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
    visit(steps)
    return actions


def _parameter_text(value):
    if isinstance(value, dict):
        return " ".join(_parameter_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_parameter_text(item) for item in value)
    return str(value or "")


def _semantic_tokens(value):
    ignored = {
        "the", "a", "an", "is", "are", "be", "been", "being", "to", "of", "in",
        "on", "at", "for", "from", "with", "and", "or", "as", "per", "page", "screen",
        "correctly", "properly", "visible", "displayed", "verify", "validate", "check",
        "button", "must", "should", "that", "this", "user", "app", "application",
    }
    return {
        token for token in re.findall(r"[a-z0-9]+", str(value or "").casefold())
        if len(token) > 2 and token not in ignored
    }


def _assertion_targets(adapted):
    targets = []
    def visit(value):
        if isinstance(value, dict):
            if value.get("command") in {"assertVisible", "assertNotVisible", "extendedWaitUntil"}:
                targets.append(_parameter_text(value.get("parameters", {})))
            for key in ("assertVisible", "assertNotVisible", "extendedWaitUntil"):
                if key in value:
                    targets.append(_parameter_text(value[key]))
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
    visit(adapted)
    return " ".join(targets)


def _semantic_error(source_step, adapted, item=None):
    """Reject superficially valid conversions that lose counts or polarity."""
    text = str(source_step or "").casefold()
    negative = bool(re.search(r"\b(?:not|no|never|absent|without)\b", text))
    actions = _actions(adapted)
    if re.search(r"\b(?:tap|click|press|select|open|navigate|go to)\b", text) and not any(
        action in {"tapOn", "runFlow", "back", "openLink"} for action in actions
    ):
        return "Requested interaction was not converted into an action"
    if negative and "assertVisible" in actions and "assertNotVisible" not in actions:
        return "Negative expectation was converted into assertVisible"
    words = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
             "seven": 7, "eight": 8, "nine": 9, "ten": 10}
    expected = None
    numeric = re.search(r"\b(\d+)\s+times?\b", text)
    if numeric:
        expected = int(numeric.group(1))
    else:
        for word, value in words.items():
            if re.search(rf"\b{word}\s+times?\b", text):
                expected = value
                break
    if expected and expected > 1:
        actual = next((step.get("parameters", {}).get("times") for step in adapted
                       if step.get("command") == "repeat"), None)
        if actual != expected:
            return f"Required repeat count {expected} was not preserved"

    explicit = bool(
        (item or {}).get("element_id")
        or (item or {}).get("automation_intent")
        or (item or {}).get("yaml_command")
        or re.match(r"\s*[A-Z_]+\s*\(", str(source_step or ""))
    )
    if not explicit and any(action in {"assertVisible", "assertNotVisible", "extendedWaitUntil"}
                            for action in actions):
        targets = _semantic_tokens(_assertion_targets(adapted))
        requirements = _semantic_tokens(source_step)
        if requirements and not requirements.intersection(targets):
            return "Generated assertion target is unrelated to the requirement"

    setup_flow = "runFlow" in actions and bool(re.search(
        r"\b(?:establish|launch|start|sign in|login)\b", text
    ))
    if not explicit and not setup_flow and re.search(
        r"\b(?:align(?:ed|ment)?|spacing|spaced|overlap(?:ping)?|responsive|"
        r"retain(?:ed|s|ing)?|remember(?:s|ed|ing)?|smooth(?:ly)?|grey|gray|"
        r"active|clickable|visual(?:ly)?|design)\b", text
    ):
        return "Visual or retained-state requirement needs explicit automatable evidence"
    return ""


def _ordered_yaml(generator, case, use_ai):
    """Convert one source row at a time so AI cannot reorder or drop the case."""
    source_items = _generation_items(case)
    generated_steps, assumptions = [], []
    traceability = []
    ai_confidences = []
    used_ai = False
    ai_fallbacks = 0
    for position, item in enumerate(source_items, start=1):
        source_step = item["text"]
        adapted = []
        grounding = []
        conversion_error = ""
        try:
            adapted = generator.generate_test([source_step], case_id=case["id"])["steps"]
            grounding.extend(generator.last_grounding_events)
            semantic_error = _semantic_error(source_step, adapted, item)
            if semantic_error:
                raise ValueError(semantic_error)
        except Exception as direct_exc:
            direct_error = str(direct_exc)
            # A syntactically generated command that fails semantic validation
            # must never survive into YAML or be counted as requirement coverage.
            adapted = []
            grounding = []
            if not use_ai:
                assumptions.append(
                    f"Source step {position} not converted: {source_step} ({direct_error})"
                )
                conversion_error = direct_error
            elif ai_fallbacks < MAX_AI_FALLBACKS_PER_CASE:
                try:
                    ai_fallbacks += 1
                    design = _ai_rewrite({**case, "steps": [source_step]})
                    unresolved = list(design.get("unresolved_assumptions", []))
                    if unresolved:
                        assumptions.extend(unresolved)
                        raise ValueError("AI adaptation requires unresolved selectors or navigation assumptions")
                    for ai_step in design["test_steps"]:
                        adapted.extend(generator.generate_test([ai_step], case_id=case["id"])["steps"])
                        grounding.extend(generator.last_grounding_events)
                    if not adapted:
                        raise ValueError("AI returned no executable commands")
                    semantic_error = _semantic_error(source_step, adapted, item)
                    if semantic_error:
                        raise ValueError(semantic_error)
                    used_ai = True
                    ai_confidences.append(float(design.get("confidence", 0)))
                except Exception as ai_exc:
                    conversion_error = f"rules: {direct_error}; AI: {ai_exc}"
                    assumptions.append(
                        f"Source step {position} not converted: {source_step} ({conversion_error})"
                    )
            else:
                conversion_error = (
                    f"rules: {direct_error}; AI fallback budget of "
                    f"{MAX_AI_FALLBACKS_PER_CASE} per case already used"
                )
                assumptions.append(
                    f"Source step {position} needs locator/test-data review: {source_step}"
                )
        actions = _actions(adapted)
        assertion_covered = any(action in {"assertVisible", "assertNotVisible", "extendedWaitUntil"}
                                for action in actions)
        covered = bool(adapted) and (assertion_covered or not item["required_assertion"])
        if adapted and not covered:
            assumptions.append(f"Expected result not validated: {item.get('expected_result', source_step)}")
        generated_steps.extend(adapted)
        traceability.append({
            "position": position, "source_type": item["source_type"],
            "step_number": item.get("step_number"), "requirement": item.get("expected_result", source_step),
            "generation_input": source_step, "commands": actions,
            "selector": item.get("element_id", ""), "status": "covered" if covered else "incomplete",
            "selector_grounding": grounding,
            "reason": conversion_error or ("No assertion generated" if adapted and not covered else ""),
            "source_sheet": item.get("source_sheet", ""), "source_row": item.get("source_row"),
        })
    # Keep the full obligation map even when deterministic rules cannot safely
    # emit a command. Friday needs this traceability to author a grounded
    # replacement. Raising here used to erase the requirements and left the
    # repair agent with an empty, impossible-to-repair draft.
    if not generated_steps:
        return ("", "rules", 0.0, list(dict.fromkeys(assumptions)), traceability)
    test = {
        "appId": generator.app_id,
        "tags": ["generated", "ordered"] + (["ai-adapted"] if used_ai else []),
        "steps": generated_steps,
    }
    coverage = sum(item["status"] == "covered" for item in traceability)
    coverage_confidence = coverage / len(traceability) if traceability else 0
    confidence = min(ai_confidences) if ai_confidences else 1.0
    confidence = min(confidence, coverage_confidence)
    return (generator.writer.write(test), ("ai" if used_ai else "rules"), confidence,
            list(dict.fromkeys(assumptions)), traceability)


def _ai_rewrite(case):
    """Ground one unsupported case against repository assets using structured AI output."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from AI.ai_scenario_expander import AIScenarioExpander

    evidence = AdaptiveTestAgent().retrieve(
        [case.get("name", ""), *case["steps"], *case.get("expected_results", [])],
        user_state=case.get("user_type", ""),
    )
    return AIScenarioExpander().expand({
        "test_case_id": case["id"], "name": case["name"],
        "module": case.get("module") or "Unassigned", "validation_points": list(case["steps"]),
        "expected_results": case.get("expected_results", []),
        "automation_intents": case.get("automation_intents", []),
        "precondition": case.get("precondition", ""),
        "test_data": case.get("test_data", ""),
        "user_type": case.get("user_type", ""),
        "app_memory_evidence": evidence,
    })


def create_drafts(excel_path, use_ai=True):
    # Keep repository demonstrations current. Previously this only happened when
    # App Memory was rebuilt manually, so newly added Common/sign-in flows were
    # invisible to Excel conversion.
    index_yaml_flows()
    normalized_folder = ROOT / "Uploads" / "Normalized"
    normalized_path = normalized_folder / f"{Path(excel_path).stem}_normalized.xlsx"
    conversion = convert_to_supported_excel(excel_path, normalized_path)
    normalization = SimpleNamespace(
        source_path=Path(excel_path),
        canonical_path=conversion["output"],
        source_format=(
            "multi-sheet test-case workbook"
            if conversion["sheets"] > 1 else "test-case workbook"
        ),
        case_count=conversion["cases"],
        step_count=conversion["steps"],
        sheet_count=conversion["sheets"],
    )
    case_limit = generation_case_limit()
    if normalization.case_count > case_limit:
        raise ValueError(
            f"Workbook contains {normalization.case_count} cases. "
            f"Your saved case-count setting allows {case_limit} cases per upload; "
            "increase it in Settings or split the workbook into complete case batches."
        )
    reader, generator, ids = ExcelReader(), YAMLGenerator(), []
    friday_single_pass = (
        use_ai and AUTO_REPAIR_PENDING_YAML and bool(os.getenv("OPENAI_API_KEY"))
    )
    for case in reader.group_cases(normalization.canonical_path):
        learned = AdaptiveTestAgent.approved_yaml(case["id"], case.get("user_type", ""))
        if learned:
            yaml_text, mode, confidence, assumptions, error = (
                learned["yaml"], "learned", 1.0,
                ["Reused accepted YAML for the same case ID and user state."], None,
            )
            traceability = [{
                "position": position, "source_type": item["source_type"],
                "step_number": item.get("step_number"),
                "requirement": item.get("expected_result", item["text"]),
                "generation_input": item["text"], "commands": ["learnedFlow"],
                "selector": item.get("element_id", ""), "status": "covered",
                "reason": "Matched accepted case/state YAML lesson.",
                "source_sheet": item.get("source_sheet", ""),
                "source_row": item.get("source_row"),
            } for position, item in enumerate(_generation_items(case), start=1)]
        else:
            try:
                # Rules establish safe commands and traceability first. Friday
                # then reasons over the complete case once, instead of making
                # a slow independent AI request for every unsupported row.
                yaml_text, mode, confidence, assumptions, traceability = _ordered_yaml(
                    generator, case, use_ai and not friday_single_pass
                )
                error = None if yaml_text else "Rules produced no safe commands; Friday review required."
            except Exception as exc:
                yaml_text, error = "", str(exc)
                mode, confidence, assumptions, traceability = "rules", 0.0, [], []
        coverage_status = "complete" if traceability and all(
            item["status"] == "covered" for item in traceability
        ) else "incomplete"
        if assumptions:
            AdaptiveTestAgent.record_learning(
                "generation_assumptions",
                {"assumptions": assumptions, "steps": case["steps"]},
                source="yaml_generation",
                confidence=confidence,
                case_id=case["id"],
            )
        with connect() as db:
            cursor = db.execute(
                """INSERT INTO drafts(case_id,name,yaml,source_file,error,generation_mode,
                   ai_confidence,ai_assumptions,traceability,coverage_status,user_state)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (case["id"], case["name"], yaml_text, Path(excel_path).name, error,
                 mode, confidence, json.dumps(assumptions, ensure_ascii=False),
                 json.dumps(traceability, ensure_ascii=False), coverage_status,
                 case.get("user_type", "")),
            )
            ids.append(cursor.lastrowid)
        selector_decisions = [
            decision for item in traceability for decision in item.get("selector_grounding", [])
        ]
        AdaptiveTestAgent.learn_from_locator_grounding(
            case["id"], case["name"], case.get("user_type", ""),
            [item.get("requirement", "") for item in traceability], selector_decisions,
        )
    if friday_single_pass:
        start_friday_repair(ids)
    return ids, normalization


def draft_guidance(draft):
    """Return Agent Workspace evidence and suggestions for a generated draft."""
    from web.services.adaptive_test_agent import AdaptiveTestAgent

    traceability = json.loads(draft["traceability"] or "[]")
    requirements = [
        item.get("requirement") or item.get("generation_input") or ""
        for item in traceability
    ]
    evidence = AdaptiveTestAgent().retrieve(
        [draft["case_id"], draft["name"], *requirements],
        limit=20, user_state=draft["user_state"] or "",
    )
    passed_flows = [item for item in evidence if item.get("evidence_type") == "passed_repository_flow"]
    failures = [
        item for item in evidence
        if item.get("evidence_type") == "negative_learning"
        and item.get("payload", {}).get("component") != "device_transport"
    ]
    validated = [item for item in evidence if item.get("validated")]
    covered = sum(item.get("status") == "covered" for item in traceability)
    coverage = covered / len(traceability) if traceability else 0.0
    suggestions = []
    if passed_flows:
        suggestions.append(
            "Reuse proven command ordering from: "
            + ", ".join(item.get("path", "approved flow") for item in passed_flows[:3]) + "."
        )
    else:
        suggestions.append(
            "No matching passed YAML was found; execute this case before promoting it as reusable evidence."
        )
    for item in failures[:3]:
        payload = item.get("payload", {})
        reason = payload.get("root_cause") or payload.get("error") or payload.get("failed_step")
        if reason:
            suggestions.append(f"Avoid related failure from {item.get('case_id') or 'prior execution'}: {reason}")
    incomplete = [item for item in traceability if item.get("status") != "covered"]
    if incomplete:
        suggestions.append(f"Complete {len(incomplete)} uncovered requirement(s) before approval.")
    confidence = min(100, round(coverage * 55) + min(25, len(passed_flows) * 8)
                     + min(20, len(validated) * 2) - min(15, len(failures) * 3))
    return {
        "confidence": max(0, confidence), "suggestions": suggestions,
        "passed_flows": passed_flows[:5], "failures": failures[:5],
        "evidence_count": len(evidence), "validated_count": len(validated),
    }


def approve_draft(draft_id, yaml_text, suite, reviewer, allow_incomplete=False):
    with connect() as db:
        draft = db.execute("SELECT * FROM drafts WHERE id=?", (draft_id,)).fetchone()
        if not draft or draft["status"] != "pending":
            raise ValueError("Draft is not pending")
        locks = json.loads(SCENARIO_LOCKS.read_text(encoding="utf-8")) \
            if SCENARIO_LOCKS.is_file() else {}
        if draft["case_id"] in locks:
            raise ValueError(
                f"Scenario {draft['case_id']} is locked against generated overwrite. "
                "Review or unlock the final scenario explicitly before replacing it."
            )
        coverage = traceability_coverage(draft["traceability"])
        if coverage <= MIN_APPROVAL_COVERAGE:
            raise ValueError(
                f"Approval blocked: requirement coverage is {coverage:.0%}; "
                f"it must be greater than {MIN_APPROVAL_COVERAGE:.0%}."
            )
        if draft["coverage_status"] != "complete" and not allow_incomplete:
            raise ValueError(
                "INCOMPLETE – REQUIREMENT NOT COVERED. Review the traceability gaps or "
                "explicitly approve the incomplete draft."
            )
        safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", draft["case_id"])
        filename = f"{safe_id}.yaml"
        (ROOT / "Scenarios" / filename).write_text(yaml_text, encoding="utf-8")
        suite_path = ROOT / "Suites" / f"{suite}.json"
        data = json.loads(suite_path.read_text(encoding="utf-8"))
        previous = next(
            (item for item in data.get("tests", []) if item.get("id") == draft["case_id"]), {}
        )
        case_prefix = str(draft["case_id"]).upper()
        if case_prefix.startswith(("ANON_HOME_", "SUB_HOME_")):
            inferred_module = "Home"
        elif case_prefix.startswith(("ANON_LOGIN_", "SUB_LOGIN_")):
            inferred_module = "Login"
        elif case_prefix.startswith(("ANON_TREND_", "SUB_TREND_")):
            inferred_module = "Trending"
        elif case_prefix.startswith(("ANON_PREM_", "SUB_PREM_")):
            inferred_module = "Premium"
        elif case_prefix.startswith(("ANON_EBOOK_", "SUB_EBOOK_")):
            inferred_module = "eBooks"
        elif case_prefix.startswith(("ANON_GAMES_", "SUB_GAMES_")):
            inferred_module = "Games"
        elif case_prefix.startswith(("ANON_HAM_", "SUB_HAM_")):
            inferred_module = "Hamburger Menu"
        elif case_prefix.startswith(("ANON_ACCOUNT_", "SUB_ACCOUNT_")):
            inferred_module = "Account Settings"
        elif case_prefix.startswith(("ANON_VIDEO_", "SUB_VIDEO_")):
            inferred_module = "Videos"
        elif case_prefix.startswith(("ANON_PHOTO_", "SUB_PHOTO_")):
            inferred_module = "Photos Quick Access"
        elif case_prefix.startswith(("ANON_PODCAST_", "SUB_PODCAST_")):
            inferred_module = "Podcast Quick Access"
        elif case_prefix.startswith(("ANON_EDITORIAL_", "SUB_EDITORIAL_")):
            inferred_module = "Editorial Quick Access"
        elif case_prefix.startswith(("ANON_OPINION_", "SUB_OPINION_")):
            inferred_module = "Opinion Quick Access"
        elif case_prefix.startswith(("ANON_BUSINESS_", "SUB_BUSINESS_", "ANON_BUS_", "SUB_BUS_")):
            inferred_module = "Business Quick Access"
        elif case_prefix.startswith(("ANON_ENTERTAINMENT_", "SUB_ENTERTAINMENT_", "ANON_ENT_", "SUB_ENT_")):
            inferred_module = "Entertainment Quick Access"
        elif case_prefix.startswith(("ANON_BOOKS_", "SUB_BOOKS_", "ANON_BOOK_", "SUB_BOOK_")):
            inferred_module = "Books Quick Access"
        elif case_prefix.startswith(("ANON_FOOD_", "SUB_FOOD_")):
            inferred_module = "Food Quick Access"
        elif case_prefix.startswith(("ANON_SPORTS_", "SUB_SPORTS_", "ANON_SPORT_", "SUB_SPORT_")):
            inferred_module = "Sports Quick Access"
        elif case_prefix.startswith(("ANON_INDIA_", "SUB_INDIA_")):
            inferred_module = "India Quick Access"
        elif case_prefix.startswith(("ANON_ARTICLE_", "SUB_ARTICLE_")):
            inferred_module = "Article Page"
        else:
            inferred_module = "AI Generated"
        module = previous.get("module")
        if not module or module == "AI Generated":
            module = inferred_module
        data["tests"] = [item for item in data.get("tests", []) if item.get("id") != draft["case_id"]]
        data["tests"].append({"id": draft["case_id"], "module": module,
                              "section": previous.get("section") or module,
                              "user_state": draft["user_state"], "priority": "P2",
                              "name": draft["name"], "yaml": filename})
        suite_path.write_text(json.dumps(data, indent=4), encoding="utf-8")
        db.execute("UPDATE drafts SET yaml=?,status='approved',reviewed_at=CURRENT_TIMESTAMP,reviewed_by=? WHERE id=?",
                   (yaml_text, reviewer, draft_id))
    AdaptiveTestAgent.learn_from_approved_yaml(
        draft["case_id"], draft["name"], yaml_text, draft["user_state"], reviewer,
    )


def reject_draft(draft_id, reviewer):
    with connect() as db:
        db.execute("UPDATE drafts SET status='rejected',reviewed_at=CURRENT_TIMESTAMP,reviewed_by=? WHERE id=? AND status='pending'",
                   (reviewer, draft_id))
