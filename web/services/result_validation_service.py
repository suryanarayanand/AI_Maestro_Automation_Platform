"""Validate a successful Maestro run against its source Excel traceability."""

import json

from web.portal_db import connect


def excel_condition_verdict(case_id, execution_status):
    """Return the segregated status and evidence for one execution result.

    Maestro proves that the generated commands ran. An Excel-backed pass also
    requires an approved draft whose source requirements are fully traced to
    executable commands and whose assertion requirements contain assertions.
    """
    normalized = str(execution_status or "").upper()
    if normalized != "PASS":
        return normalized, "execution_failed", "Maestro execution did not pass."

    with connect() as db:
        draft = db.execute(
            """SELECT source_file,coverage_status,traceability FROM drafts
               WHERE case_id=? AND status='approved' ORDER BY id DESC LIMIT 1""",
            (case_id,),
        ).fetchone()
    if not draft:
        return "NEEDS_REVIEW", "missing_excel_traceability", (
            "Maestro passed, but no approved Excel-backed draft was found."
        )

    try:
        traceability = json.loads(draft["traceability"] or "[]")
    except json.JSONDecodeError:
        traceability = []
    incomplete = [item for item in traceability if item.get("status") != "covered"]
    assertion_commands = {"assertVisible", "assertNotVisible", "extendedWaitUntil"}
    missing_assertions = [
        item for item in traceability
        if item.get("source_type") == "expected_result"
        and not assertion_commands.intersection(item.get("commands") or [])
    ]
    if draft["coverage_status"] != "complete" or not traceability or incomplete:
        return "NEEDS_REVIEW", "incomplete_excel_coverage", (
            f"Maestro passed, but {len(incomplete)} Excel requirement(s) are incomplete."
        )
    if missing_assertions:
        return "NEEDS_REVIEW", "expected_result_not_asserted", (
            f"Maestro passed, but {len(missing_assertions)} expected result(s) lack runtime assertions."
        )
    return "PASS", "verified_excel_pass", (
        f"Maestro passed and all {len(traceability)} requirements from "
        f"{draft['source_file'] or 'the source Excel workbook'} are covered."
    )
