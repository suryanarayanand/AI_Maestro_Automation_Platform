import json
from pathlib import Path

from Utils.combined_bug_ai import synthesize_bug_report


def _severity(ai_details, visual_details, execution_failed):
    ranks = {"LOW": 1, "MINOR": 1, "MEDIUM": 2, "MAJOR": 2, "HIGH": 3, "CRITICAL": 3}
    highest = 3 if execution_failed else 1
    for item in ai_details:
        highest = max(highest, ranks.get(str(item.get("severity", "")).upper(), 1))
    for detail in visual_details:
        for issue in detail.get("ai_analysis", {}).get("issues", []):
            highest = max(highest, ranks.get(str(issue.get("severity", "")).upper(), 1))
    return {1: "Minor", 2: "Major", 3: "Critical"}[highest]


def generate_bug_summary(results, ai_summary, visual_summary, suite_name, execution_time):
    visual_by_id = {item.get("scenario"): item for item in visual_summary.get("results", [])}
    bugs = []
    counts = {"critical": 0, "major": 0, "minor": 0}

    for scenario in results:
        scenario_id = scenario["id"]
        execution_failed = scenario["status"] != "PASS"
        ai_details = [d for d in scenario.get("ai_details", []) if d.get("status") != "PASS"]
        visual_case = visual_by_id.get(scenario_id, {})
        visual_details = [d for d in visual_case.get("details", []) if d.get("status") != "PASS"]
        if not execution_failed and not ai_details and not visual_details:
            continue

        sources = []
        if execution_failed:
            sources.append("Run")
        if ai_details:
            sources.append("Screenshot AI")
        if visual_details:
            sources.append("Visual")
        severity = _severity(ai_details, visual_details, execution_failed)
        counts[severity.lower()] += 1

        ai_findings = [{
            "reason": d.get("reason", ""),
            "severity": d.get("severity", ""),
            "issues": d.get("issues", []),
        } for d in ai_details]
        visual_findings = [{
            "image": d.get("image", ""),
            "similarity": d.get("similarity"),
            "normalized": d.get("normalized", False),
            "summary": d.get("ai_analysis", {}).get("summary", ""),
            "issues": d.get("ai_analysis", {}).get("issues", []),
        } for d in visual_details]
        screenshots = list(scenario.get("screenshots", []))
        comparison_images = []
        for d in visual_details:
            comparison_images.extend(filter(None, [d.get("reference"), d.get("actual"), d.get("difference")]))

        bugs.append({
            "bug_id": f"BUG-{len(bugs) + 1:03}",
            "scenario_id": scenario_id,
            "scenario_name": scenario["name"],
            "module": scenario["module"],
            "status": "ISSUE",
            "execution_status": scenario["status"],
            "bug_type": "Combined evidence",
            "severity": severity,
            "confidence": 95 if len(sources) > 1 else 80,
            "reason": "Evidence detected by " + ", ".join(sources),
            "execution_time": scenario["duration"],
            "log_file": Path(scenario["log_file"]).name,
            "log_path": scenario["log_file"],
            "screenshots": screenshots,
            "comparison_images": comparison_images,
            "sources": sources,
            "ai_findings": ai_findings,
            "visual_findings": visual_findings,
            "recommendation": "Review the combined execution, screenshot-AI, and visual evidence.",
        })

    return {
        "suite": suite_name,
        "execution_time": execution_time,
        "summary": {
            "total": len(results), "passed": len(results) - len(bugs), "failed": len(bugs),
            **counts,
        },
        "device_comparison": {
            "reference": visual_summary.get("reference") or {"status": "Metadata unavailable"},
            "actual": visual_summary.get("actual") or {"status": "Metadata unavailable"},
        },
        "ai_synthesis": synthesize_bug_report(bugs),
        "bugs": bugs,
    }


def save_bug_summary(summary, execution_folder):
    output = Path(execution_folder) / "Bug_Summary.json"
    output.write_text(json.dumps(summary, indent=4, ensure_ascii=False), encoding="utf-8")
    return output
