import json
import os

from openai import OpenAI


def synthesize_bug_report(cases):
    """Use one AI call to turn run, screenshot-AI and visual evidence into a release summary."""
    if not cases:
        return {
            "executive_summary": "No execution, screenshot-AI, or visual issues were detected.",
            "release_recommendation": "No blocking evidence was found.",
            "top_risks": [],
        }
    compact = []
    for case in cases:
        compact.append({
            "scenario": case["scenario_id"],
            "execution_status": case["execution_status"],
            "sources": case["sources"],
            "screenshot_ai": case.get("ai_findings", []),
            "visual": case.get("visual_findings", []),
        })
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.responses.create(
            model="gpt-4.1",
            input=[{
                "role": "user",
                "content": [{
                    "type": "input_text",
                    "text": (
                        "You are a senior mobile QA lead. Combine the Maestro execution, "
                        "screenshot AI, and cross-device visual evidence below. Distinguish "
                        "functional failures from visual-only findings and dynamic-content noise. "
                        "Return only JSON with keys executive_summary, release_recommendation, "
                        "and top_risks (array of short strings).\n\n" + json.dumps(compact)
                    ),
                }],
            }],
        )
        raw = response.output_text.strip()
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.endswith("```"):
            raw = raw[:-3]
        return json.loads(raw.strip())
    except Exception as exc:
        return {
            "executive_summary": f"{len(cases)} scenarios contain combined AI or visual evidence.",
            "release_recommendation": "Review the combined evidence before release.",
            "top_risks": [],
            "ai_error": str(exc),
        }
