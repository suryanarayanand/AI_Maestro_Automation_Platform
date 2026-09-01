"""Grounded conversational assistant for portal testing questions."""

import json
import hashlib
import os
import re
from pathlib import Path

from web.portal_db import connect
from web.services.adaptive_test_agent import AdaptiveTestAgent, classify_execution_failure
from web.services.testing_bot_repair_service import build_repair_proposal

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

ROOT = Path(__file__).resolve().parents[2]

CASE_TOKEN = re.compile(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b", re.I)
ACCEPT_TERMS = re.compile(r"\b(?:accept|apply|use|update)\b.*\b(?:suggestion|proposed|yaml|change)\b", re.I)

MODULE_TERMS = {
    "Article Page": ("article", "paywall", "headline", "recommended", "listen"),
    "Home": ("home", "homepage"), "Trending": ("trending",),
    "Premium": ("premium", "briefing"), "eBooks": ("ebook", "e-book"),
    "Games": ("game", "sudoku", "quiz"), "Login": ("login", "sign in", "signin"),
    "Hamburger Menu": ("hamburger", "drawer", "menu"),
    "Account Settings": ("account", "appearance", "theme"),
    "Videos": ("video",), "Photos Quick Access": ("photo", "gallery"),
    "Editorial Quick Access": ("editorial",), "Opinion Quick Access": ("opinion",),
    "Podcast Quick Access": ("podcast",),
    "Business Quick Access": ("business",),
    "Entertainment Quick Access": ("entertainment",),
    "Books Quick Access": ("books",), "Food Quick Access": ("food",),
    "Sports Quick Access": ("sports",), "India Quick Access": ("india",),
}


def _request_profile(question):
    lowered = str(question or "").casefold()
    states = []
    for state, terms in {
        "ANONYMOUS": ("anonymous", "signed out", "logged out"),
        "SUBSCRIBER": ("subscriber", "subscribed"),
        "REGISTERED_USER": ("registered", "non subscriber", "non-subscriber"),
        "EXPIRED_USER": ("expired", "lapsed"),
    }.items():
        if any(term in lowered for term in terms):
            states.append(state)
    modules = [name for name, terms in MODULE_TERMS.items() if any(term in lowered for term in terms)]
    cases = list(dict.fromkeys(item.upper() for item in CASE_TOKEN.findall(question)))
    intents = []
    for intent, terms in {
        "failure_analysis": ("fail", "error", "why", "automation issue", "bug"),
        "coverage_analysis": ("coverage", "covered", "missing", "gap"),
        "yaml_review": ("yaml", "repair", "fix", "approve", "pending"),
        "execution_status": ("running", "run status", "job", "stalled", "stuck"),
        "case_design": ("test case", "scenario", "steps", "create case"),
        "reference_search": ("url", "reference", "article type", "locator"),
        "recommendation": ("suggest", "recommend", "next", "improve"),
    }.items():
        if any(term in lowered for term in terms):
            intents.append(intent)
    return {"intents": intents or ["testing_question"], "modules": modules,
            "user_states": states, "case_ids": cases}


def _portal_snapshot(profile):
    """Small structured operating picture for testing decisions."""
    with connect() as db:
        jobs = [dict(row) for row in db.execute(
            "SELECT id,suite,status,current_case,completed,total,started_at,finished_at "
            "FROM jobs ORDER BY id DESC LIMIT 8"
        ).fetchall()]
        pending = [dict(row) for row in db.execute(
            "SELECT case_id,name,user_state,coverage_status,ai_confidence FROM drafts "
            "WHERE status='pending' ORDER BY id DESC LIMIT 30"
        ).fetchall()]
        failures = [dict(row) for row in db.execute(
            """SELECT r.case_id,r.name,r.status,r.execution_status,r.condition_status,
                      r.duration,r.stdout,r.stderr,r.job_id
               FROM job_results r WHERE UPPER(r.status) IN ('FAIL','FAILED','CANCELLED')
               ORDER BY r.id DESC LIMIT 12"""
        ).fetchall()]
        article_count = db.execute(
            "SELECT COUNT(*) FROM article_references WHERE active=1"
        ).fetchone()[0]
        article_types = [row[0] for row in db.execute(
            "SELECT article_type FROM article_references WHERE active=1 "
            "GROUP BY article_type ORDER BY COUNT(*) DESC,article_type LIMIT 15"
        ).fetchall()]
    suite_inventory = {}
    requested_states = {str(state).upper() for state in profile.get("user_states", [])}
    suite_key = (
        "user_subscriber" if "SUBSCRIBER" in requested_states else
        "user_registered" if "REGISTERED" in requested_states else
        "user_expired" if "EXPIRED" in requested_states else
        "user_anonymous"
    )
    suite_path = ROOT / "Suites" / f"{suite_key}.json"
    if suite_path.is_file():
        try:
            suite_data = json.loads(suite_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            suite_data = {}
        for item in suite_data.get("tests", []):
            module = item.get("module") or "Unassigned"
            suite_inventory[module] = suite_inventory.get(module, 0) + 1
    requested_modules = {
        module: suite_inventory.get(module, 0) for module in profile.get("modules", [])
    }
    failure_summaries = []
    for row in failures:
        diagnosis = classify_execution_failure((row.get("stderr") or "") + "\n" + (row.get("stdout") or ""))
        failure_summaries.append({k: row.get(k) for k in (
            "case_id", "name", "status", "execution_status", "condition_status", "duration", "job_id"
        )} | diagnosis)
    return {"request": profile, "recent_jobs": jobs, "pending_drafts": pending,
            "recent_failures": failure_summaries, "article_library": {
                "active_urls": article_count, "common_types": article_types,
            }, "suite_key": suite_key, "suite_inventory": suite_inventory,
            "requested_module_cases": requested_modules}


def _memory_tokens(value):
    ignored = {"the", "and", "for", "with", "that", "this", "yaml", "case", "please", "okay"}
    return {item for item in re.findall(r"[a-z0-9_]+", str(value or "").casefold())
            if len(item) > 2 and item not in ignored}


def _relevant_chat_memory(question, username, limit=12):
    """Retrieve durable prior conversation as context, never executable truth."""
    wanted = _memory_tokens(question)
    if not wanted:
        return []
    with connect() as db:
        rows = db.execute(
            """SELECT id,role,message FROM testing_bot_messages
               WHERE username=? ORDER BY id DESC LIMIT 1000""", (username or "",),
        ).fetchall()
    ranked = []
    for row in rows:
        overlap = wanted & _memory_tokens(row["message"])
        if overlap:
            ranked.append((len(overlap), int(row["id"]), dict(row)))
    ranked.sort(key=lambda item: (-item[0], -item[1]))
    return [item for _, _, item in ranked[:limit]]


def _friday_answer(question, username, evidence, profile=None, snapshot=None):
    """Use the model for conversation only; portal mutations stay deterministic."""
    if OpenAI is None or not os.getenv("OPENAI_API_KEY"):
        return None
    with connect() as db:
        rows = db.execute(
            """SELECT role,message FROM testing_bot_messages WHERE username=?
               ORDER BY id DESC LIMIT 10""", (username or "",),
        ).fetchall()
    conversation = list(reversed([dict(row) for row in rows]))
    relevant_memory = _relevant_chat_memory(question, username)
    prompt = f"""You are Friday, a senior mobile QA lead and Maestro automation architect inside AI Maestro.
Answer using only the supplied portal evidence and recent conversation. You understand Maestro
YAML, test design, modules, user states, execution diagnosis, risk and requirement coverage.
First interpret the tester's objective using the structured request profile. Correlate Excel/YAML
coverage, approved behavior, Article Library data, locators, passed flows and current/recent runs.
Clearly distinguish automation failure, application bug, environment/setup failure, expected
conditional behavior, and missing evidence. Never claim you ran,
changed, approved, deleted, or started anything. Controlled portal mutations are handled separately.
Do not invent locators, results, credentials, or app behavior. If evidence is insufficient, state
what should be inspected next. Do not give generic QA advice when portal-specific evidence exists.
For analysis answers use compact sections: Understanding, Evidence, Assessment, Recommendation,
and Next action. Omit a section only when it adds no value.

Structured request profile:
{json.dumps(profile or {}, ensure_ascii=False, default=str)}

Portal operating snapshot:
{json.dumps(snapshot or {}, ensure_ascii=False, default=str)}

Recent conversation:
{json.dumps(conversation, ensure_ascii=False, default=str)}

Relevant durable chat memory (context only; not validated selectors or execution truth):
{json.dumps(relevant_memory, ensure_ascii=False, default=str)}

Portal evidence:
{json.dumps(evidence, ensure_ascii=False, default=str)}

Tester: {question}
Friday:"""
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=float(os.getenv("OPENAI_TESTING_BOT_TIMEOUT", "25")), max_retries=0)
        response = client.responses.create(
            model=os.getenv("OPENAI_TESTING_BOT_MODEL", os.getenv("OPENAI_SCENARIO_MODEL", "gpt-5.6-sol")),
            input=prompt,
        )
        return str(response.output_text or "").strip() or None
    except Exception:
        return None


def _coverage(traceability):
    try:
        items = json.loads(traceability or "[]") if isinstance(traceability, str) else traceability
    except json.JSONDecodeError:
        items = []
    return (sum(item.get("status") == "covered" for item in items) / len(items)) if items else 0.0


def _traceability_items(traceability):
    try:
        value = json.loads(traceability or "[]") if isinstance(traceability, str) else traceability
    except json.JSONDecodeError:
        value = []
    return value if isinstance(value, list) else []


def _uncovered(traceability):
    missing = []
    for item in _traceability_items(traceability):
        if item.get("status") == "covered":
            continue
        text = item.get("requirement") or item.get("obligation") or item.get("step") or item.get("text")
        missing.append(str(text or "Imported obligation without an executable command").strip())
    return list(dict.fromkeys(missing))


def _pending_case(question):
    tokens = [item.upper() for item in CASE_TOKEN.findall(question)]
    if not tokens:
        return None
    with connect() as db:
        for token in tokens:
            row = db.execute(
                "SELECT * FROM drafts WHERE case_id=? AND status='pending' ORDER BY id DESC LIMIT 1",
                (token,),
            ).fetchone()
            if row:
                return row
    return None


def _proposal_for(draft):
    """Create a reviewable proposal; applying it is a separate user-authorized action."""
    yaml_text = str(draft["yaml"] or "")
    traceability = str(draft["traceability"] or "[]")
    coverage = _coverage(traceability)
    if not yaml_text.strip():
        raise ValueError("This draft has no executable YAML to propose yet.")
    evidence = AdaptiveTestAgent().retrieve(
        [draft["case_id"], draft["name"], traceability], limit=20,
        user_state=draft["user_state"] or "",
    )
    references = [
        item.get("path") or item.get("locator_value") or item.get("rule_id")
        for item in evidence if item.get("validated")
    ]
    return {
        "action": "yaml_proposal", "draft_id": draft["id"],
        "case_id": draft["case_id"], "yaml": yaml_text,
        "traceability": traceability, "coverage_status": draft["coverage_status"],
        "coverage": coverage, "source_hash": hashlib.sha256(yaml_text.encode("utf-8")).hexdigest(),
        "uncovered": _uncovered(traceability),
        "references": [item for item in references if item][:8],
    }


def _repair_proposal_for(draft):
    repaired = build_repair_proposal(draft)
    yaml_text = str(repaired["yaml"])
    return {
        "action": "yaml_proposal", "proposal_kind": "evidence_grounded_repair",
        "draft_id": draft["id"], "case_id": draft["case_id"],
        "yaml": yaml_text,
        "traceability": json.dumps(repaired["traceability"], ensure_ascii=False),
        "coverage_status": "complete", "coverage": 1.0, "uncovered": [],
        # Acceptance must still prove that the underlying draft did not change
        # while the repair was being reviewed.
        "source_hash": hashlib.sha256(str(draft["yaml"] or "").encode("utf-8")).hexdigest(),
        "references": repaired["references"],
    }


def _latest_proposal(username):
    with connect() as db:
        rows = db.execute(
            """SELECT evidence FROM testing_bot_messages
               WHERE username=? AND role='assistant' ORDER BY id DESC LIMIT 30""",
            (username,),
        ).fetchall()
    for row in rows:
        try:
            value = json.loads(row["evidence"] or "null")
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("action") == "yaml_proposal":
            return value
    return None


def _apply_proposal(username):
    proposal = _latest_proposal(username)
    if not proposal:
        raise ValueError("No pending bot YAML suggestion was found. Ask me to review a case first.")
    if float(proposal.get("coverage") or 0) < 1 or proposal.get("coverage_status") != "complete":
        missing = proposal.get("uncovered") or []
        detail = "; ".join(missing[:4]) or "one or more imported obligations"
        raise ValueError(
            f"I did not update {proposal.get('case_id', 'the case')}: the suggestion covers only "
            f"{float(proposal.get('coverage') or 0):.0%}. Missing: {detail}. "
            "Friday may apply a suggestion only after requirement coverage reaches 100%."
        )
    with connect() as db:
        draft = db.execute("SELECT * FROM drafts WHERE id=?", (proposal["draft_id"],)).fetchone()
        if not draft or draft["status"] != "pending":
            raise ValueError("The proposed draft is no longer pending, so I did not change it.")
        current_hash = hashlib.sha256(str(draft["yaml"] or "").encode("utf-8")).hexdigest()
        if current_hash != proposal["source_hash"]:
            raise ValueError("The YAML changed after my suggestion. Review it again before applying changes.")
        db.execute(
            """UPDATE drafts SET yaml=?,traceability=?,coverage_status=?,
               ai_confidence=?,generation_mode='bot-accepted',error=NULL WHERE id=?""",
            (proposal["yaml"], proposal["traceability"], proposal["coverage_status"],
             proposal["coverage"], proposal["draft_id"]),
        )
    return (
        f"Applied the accepted testing-bot suggestion to pending case {proposal['case_id']}. "
        f"Requirement coverage is {proposal['coverage']:.0%}. The case still requires normal YAML approval.",
        {"action": "yaml_applied", "case_id": proposal["case_id"],
         "draft_id": proposal["draft_id"], "coverage": proposal["coverage"]},
    )


def answer(question, username=None):
    question = str(question or "").strip()
    if not question:
        raise ValueError("Enter a testing question.")
    if username and ACCEPT_TERMS.search(question):
        return _apply_proposal(username)

    profile = _request_profile(question)
    snapshot = _portal_snapshot(profile)

    pending = _pending_case(question)
    lowered = question.casefold()
    if pending and re.search(r"\b(?:fix|repair|complete|improve|rewrite)\b", lowered):
        try:
            proposal = _repair_proposal_for(pending)
        except ValueError as exc:
            return (
                f"I could not safely complete {pending['case_id']}. {exc} "
                "I did not change the draft. Suggested next action: capture the live UI hierarchy "
                "on the required state, validate the missing selector/state property, then ask me "
                f"to repair {pending['case_id']} again.",
                {"action": "yaml_repair_blocked", "case_id": pending["case_id"],
                 "reason": str(exc), "changed": False},
            )
        refs = ", ".join(proposal["references"]) or "validated repository evidence"
        return (
            f"Evidence-grounded repair proposal for {pending['case_id']}. Coverage: 100%. "
            f"Grounding: {refs}.\n\n{proposal['yaml']}\n"
            "Review the commands. If correct, say: Accept the bot suggestion and update the YAML.",
            proposal,
        )
    if re.search(r"\b(?:review|show|list|check)\b.*\bpending\b", lowered):
        with connect() as db:
            rows = db.execute(
                """SELECT case_id,name,coverage_status,ai_confidence FROM drafts
                   WHERE status='pending' ORDER BY id"""
            ).fetchall()
        if not rows:
            return "There are no pending YAML drafts.", {"action": "pending_case_list", "cases": []}
        cases = [{"case_id": row["case_id"], "name": row["name"],
                  "coverage": float(row["ai_confidence"] or 0)} for row in rows]
        summary = "; ".join(
            f"{item['case_id']} ({item['coverage']:.0%})" for item in cases
        )
        return (
            "Pending YAML cases: " + summary + ". Send one case ID to receive its grounded YAML proposal.",
            {"action": "pending_case_list", "cases": cases, "profile": profile},
        )

    if re.search(r"\b(?:upload|uploaded|uploading|import|imported)\b", lowered):
        with connect() as db:
            rows = db.execute(
                """SELECT source_file,status,coverage_status,COUNT(*) count,MAX(id) latest_id
                   FROM drafts GROUP BY source_file,status,coverage_status
                   ORDER BY latest_id DESC LIMIT 8"""
            ).fetchall()
        if not rows:
            return "No imported YAML-review records were found.", {"action": "import_status", "sources": []}
        sources = [dict(row) for row in rows]
        summary = "; ".join(
            f"{row['source_file']}: {row['count']} {row['status']} ({row['coverage_status']})"
            for row in sources
        )
        return "Latest imported review records: " + summary, {"action": "import_status", "sources": sources}

    # A pending case ID is itself an unambiguous review request. Resolve it
    # before run-history lookup, which previously produced "could not find".
    if pending:
        proposal = _proposal_for(pending)
        refs = ", ".join(proposal["references"]) or "the draft traceability"
        missing = proposal.get("uncovered") or []
        missing_text = ""
        instruction = "If this is correct, say: Accept the bot suggestion and update the YAML."
        if proposal["coverage"] < 1 or proposal["coverage_status"] != "complete":
            missing_text = "\n\nMissing executable obligations:\n- " + "\n- ".join(missing[:8] or ["Traceability is incomplete."])
            instruction = "This proposal is incomplete and cannot be applied. Add executable commands for every missing obligation first."
        response = (
            f"Testing-only YAML proposal for {pending['case_id']}. "
            f"Coverage: {proposal['coverage']:.0%}. Grounding: {refs}.\n\n"
            f"{proposal['yaml']}{missing_text}\n{instruction}"
        )
        return response, proposal

    case = re.search(r"\b(?:MANUAL_[A-Z0-9_]+|HAM_OPT_\d+|THCAT_\d+|TH_\d+|ANON_[A-Z0-9_]+|SUB_[A-Z0-9_]+)\b", question, re.I)
    if case:
        case_id = case.group(0).upper()
        with connect() as db:
            step = db.execute("SELECT * FROM atomic_flow_steps WHERE case_id=?", (case_id,)).fetchone()
            draft = db.execute("SELECT * FROM drafts WHERE case_id=? ORDER BY id DESC LIMIT 1", (case_id,)).fetchone()
            result = db.execute(
                """SELECT r.*,j.id job_id FROM job_results r JOIN jobs j ON j.id=r.job_id
                   WHERE r.case_id=? OR r.case_id LIKE ? ORDER BY r.id DESC LIMIT 1""",
                (case_id, f"{case_id}%"),
            ).fetchone()
        parts = [f"{case_id} is {step['status']} with user state {step['user_state']}." if step else ""]
        if draft:
            parts.append(
                f"YAML review is {draft['status']} with {_coverage(draft['traceability']):.0%} requirement coverage."
            )
        scenario = Path("Scenarios") / f"{case_id}.yaml"
        if scenario.is_file():
            parts.append(f"Executable scenario exists at {scenario.as_posix()}.")
        if result:
            parts.append(f"Latest job #{result['job_id']}: Maestro={result['execution_status'] or result['status']}, portal verdict={result['status']}, duration={result['duration']:.1f}s.")
            failed = next((line.strip() for line in reversed((result["stdout"] + result["stderr"]).splitlines()) if "FAILED" in line), "")
            if failed:
                parts.append(f"Failure point: {failed}")
        return " ".join(filter(None, parts)) or f"I could not find {case_id}.", [f"case:{case_id}"]

    if any(term in lowered for term in ("running", "latest run", "job status", "failed today")):
        with connect() as db:
            jobs = db.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT 5").fetchall()
        return "Recent jobs: " + "; ".join(f"#{row['id']} {row['suite']} - {row['status']} ({row['completed']}/{row['total']})" for row in jobs), [f"job:{row['id']}" for row in jobs]
    if ("anonymous" in lowered or "subscriber" in lowered) and profile["intents"] == ["testing_question"]:
        return ("Anonymous flows clear state and require SUBSCRIBE plus ADVERTISEMENT. Subscriber flows clear state, authenticate again, and require both to be absent.", ["OPEN_ANONYMOUS_HOME.yaml", "OPEN_SUBSCRIBER_HOME.yaml"])

    requested_state = profile["user_states"][0] if len(profile["user_states"]) == 1 else ""
    evidence = AdaptiveTestAgent().retrieve([question, *profile["modules"], *profile["case_ids"]],
                                            limit=24, user_state=requested_state)
    passed = [item for item in evidence if item.get("evidence_type") == "passed_repository_flow"]
    failures = [item for item in evidence if item.get("evidence_type") == "negative_learning"]
    locators = [item for item in evidence if item.get("locator_value")]
    rules = [item for item in evidence if item.get("evidence_type") == "approved_behavior_rule"]
    parts = [
        "Understanding: " + ", ".join(profile["intents"])
        + (f" for {', '.join(profile['modules'])}" if profile["modules"] else "") + ".",
        f"Evidence: {len(evidence)} relevant App Memory records; "
        f"{snapshot['article_library']['active_urls']} active Article Library URLs; "
        f"{len(snapshot['pending_drafts'])} recent pending drafts.",
    ]
    if rules:
        parts.append("Approved app behavior: " + " ".join(
            f"{item['rule_id']} - {item['expected_behavior']}" for item in rules[:2]
        ))
    if passed:
        parts.append("Passed flows: " + ", ".join(item["path"] for item in passed[:3]) + ".")
    if locators:
        parts.append("Validated selectors: " + ", ".join(item["locator_value"] for item in locators[:5]) + ".")
    reasons = [item.get("payload", {}).get("root_cause") for item in failures[:2]]
    if any(reasons):
        parts.append("Known risk: " + "; ".join(filter(None, reasons)) + ".")
    if not passed:
        parts.append("No matching passed YAML proves this behavior yet; run one reviewed case first.")
    if "failure_analysis" in profile["intents"] and snapshot["recent_failures"]:
        latest = snapshot["recent_failures"][0]
        parts.append(
            "Assessment: latest relevant failure evidence is "
            f"{latest.get('case_id')} in job #{latest.get('job_id')}; "
            f"classification={latest.get('classification')}, component={latest.get('component')}. "
            f"{latest.get('root_cause')}"
        )
        matching_failure = next(
            (item for item in failures
             if item.get("case_id") == latest.get("case_id")
             and item.get("payload", {}).get("video_failure_plan")),
            None,
        )
        if matching_failure:
            video_plan = matching_failure["payload"]["video_failure_plan"]
            frames = video_plan.get("evidence_frames") or []
            parts.append(
                "Failure video evidence: retained at "
                f"{video_plan.get('video') or 'the case evidence folder'} with "
                f"{len(frames)} extracted review frame(s). "
                f"Probable cause: {video_plan.get('probable_cause') or 'review required'}."
            )
    if "coverage_analysis" in profile["intents"]:
        incomplete = [item for item in snapshot["pending_drafts"] if item.get("coverage_status") != "complete"]
        module_detail = ", ".join(
            f"{module}={count} approved suite case(s)"
            for module, count in snapshot["requested_module_cases"].items()
        ) or "no specific module was detected"
        parts.append(
            f"Assessment: {module_detail}; {len(incomplete)} of the "
            f"{len(snapshot['pending_drafts'])} recent pending drafts still have incomplete executable coverage."
        )
    parts.append("Next action: review the cited evidence, then run only an approved module or affected failed cases.")
    article_refs = [item for item in evidence if item.get("evidence_type") == "article_reference"]
    if article_refs:
        parts.append("Controlled article references: " + ", ".join(
            f"{item['article_type']} (#{item['reference_id']})" for item in article_refs[:5]
        ) + ".")
    refs = [item.get("path") or item.get("case_id") or item.get("locator_value")
            or item.get("rule_id") or (f"article:{item.get('reference_id')}" if item.get("reference_id") else None)
            for item in evidence]
    grounded_refs = [ref for ref in refs if ref]
    friday = _friday_answer(question, username, evidence, profile, snapshot)
    return friday or " ".join(parts), grounded_refs


def chat(username, question):
    response, evidence = answer(question, username=username)
    with connect() as db:
        db.execute("INSERT INTO testing_bot_messages(username,role,message) VALUES(?,?,?)", (username, "user", question))
        db.execute("INSERT INTO testing_bot_messages(username,role,message,evidence) VALUES(?,?,?,?)", (username, "assistant", response, json.dumps(evidence)))
    return {"answer": response, "evidence": evidence}


def history(username, limit=50):
    with connect() as db:
        rows = db.execute("SELECT * FROM testing_bot_messages WHERE username=? ORDER BY id DESC LIMIT ?", (username, limit)).fetchall()
    return list(reversed([dict(row) for row in rows]))


def clear_history(username):
    """Clear only visible conversation; durable App Memory is separate."""
    with connect() as db:
        cursor = db.execute("DELETE FROM testing_bot_messages WHERE username=?", (username,))
    return cursor.rowcount
