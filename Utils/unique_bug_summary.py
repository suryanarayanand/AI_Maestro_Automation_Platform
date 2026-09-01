import json
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path


STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "detected", "evidence",
    "for", "from", "in", "is", "it", "of", "on", "or", "run", "screen", "that",
    "the", "this", "to", "ui", "was", "with",
}
GENERIC_REASONS = {"evidence detected by run", "evidence detected by visual", ""}
SEVERITY_RANK = {"minor": 1, "low": 1, "major": 2, "medium": 2, "critical": 3, "high": 3}


def _flatten(value):
    if isinstance(value, dict):
        return " ".join(_flatten(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_flatten(item) for item in value)
    return str(value or "")


def _finding_text(bug):
    parts = []
    reason = str(bug.get("reason", "")).strip()
    if reason.casefold() not in GENERIC_REASONS and not reason.casefold().startswith("evidence detected by"):
        parts.append(reason)
    for finding in bug.get("ai_findings", []):
        finding_text = " ".join([_flatten(finding.get("reason")), _flatten(finding.get("issues"))])
        if "no genuine ui" not in finding_text.casefold() and "no genuine visual" not in finding_text.casefold():
            parts.append(finding_text)
    for finding in bug.get("visual_findings", []):
        finding_text = " ".join([_flatten(finding.get("summary")), _flatten(finding.get("issues"))])
        if "no genuine ui" not in finding_text.casefold() and "no genuine visual" not in finding_text.casefold():
            parts.append(finding_text)
    return " ".join(part for part in parts if part.strip()).strip()


def _declares_non_bug(bug):
    text = _flatten([bug.get("ai_findings", []), bug.get("visual_findings", [])]).casefold()
    return "no genuine ui" in text or "no genuine visual" in text


def _tokens(text):
    return [
        token for token in re.findall(r"[a-z0-9]+", text.casefold())
        if len(token) > 2 and token not in STOP_WORDS
    ]


def _cosine(left, right, document_frequency, document_count):
    left_counts, right_counts = Counter(left), Counter(right)
    shared = set(left_counts) & set(right_counts)
    if len(shared) < 2:
        return 0.0

    def vector(counts):
        return {
            token: count * (math.log((document_count + 1) / (document_frequency[token] + 1)) + 1)
            for token, count in counts.items()
        }

    left_vector, right_vector = vector(left_counts), vector(right_counts)
    dot = sum(left_vector[token] * right_vector[token] for token in shared)
    left_size = math.sqrt(sum(value * value for value in left_vector.values()))
    right_size = math.sqrt(sum(value * value for value in right_vector.values()))
    return dot / (left_size * right_size) if left_size and right_size else 0.0


def _highest_severity(bugs):
    return max(
        (str(item.get("severity", "Minor")) for item in bugs),
        key=lambda value: SEVERITY_RANK.get(value.casefold(), 1),
        default="Minor",
    )


def generate_unique_bug_summary(report_root, similarity_threshold=0.58):
    report_root = Path(report_root)
    generated_at = datetime.now().astimezone()
    reset_marker = report_root / "Unique_Bug_Summary_Reset.json"
    reset_at = None
    if reset_marker.is_file():
        try:
            marker_data = json.loads(reset_marker.read_text(encoding="utf-8-sig"))
            reset_at = datetime.fromisoformat(marker_data.get("reset_at", "")).timestamp()
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            reset_at = None
    records = []
    source_reports = 0
    for summary_path in sorted(report_root.glob("*/Bug_Summary.json")):
        if reset_at is not None and summary_path.stat().st_mtime < reset_at:
            continue
        try:
            data = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        source_reports += 1
        for bug in data.get("bugs", []):
            item = dict(bug)
            item["report"] = summary_path.parent.name
            item["finding_text"] = _finding_text(item)
            item["tokens"] = _tokens(item["finding_text"])
            # Execution failures without a concrete finding belong in the run report,
            # not the product bug sheet. This also prevents YAML/automation failures
            # from being misreported as application defects.
            if not item["finding_text"]:
                continue
            records.append(item)

    document_frequency = Counter()
    for record in records:
        document_frequency.update(set(record["tokens"]))

    clusters = []
    for record in records:
        matched = None
        scenario_id = str(record.get("scenario_id", "")).casefold()
        for cluster in clusters:
            same_scenario = scenario_id and scenario_id in cluster["scenario_ids"]
            similar = bool(record["tokens"] and cluster["tokens"]) and _cosine(
                record["tokens"], cluster["tokens"], document_frequency, len(records)
            ) >= similarity_threshold
            if same_scenario or similar:
                matched = cluster
                break
        if matched is None:
            clusters.append({
                "scenario_ids": {scenario_id} if scenario_id else set(),
                "tokens": record["tokens"],
                "records": [record],
            })
        else:
            matched["records"].append(record)
            if scenario_id:
                matched["scenario_ids"].add(scenario_id)
            if len(record["finding_text"]) > len(matched["records"][0]["finding_text"]):
                matched["tokens"] = record["tokens"]

    merged = True
    while merged:
        merged = False
        for left_index, left in enumerate(clusters):
            for right_index in range(left_index + 1, len(clusters)):
                right = clusters[right_index]
                same_scenario = bool(left["scenario_ids"] & right["scenario_ids"])
                similar = bool(left["tokens"] and right["tokens"]) and _cosine(
                    left["tokens"], right["tokens"], document_frequency, len(records)
                ) >= similarity_threshold
                if same_scenario or similar:
                    left["records"].extend(right["records"])
                    left["scenario_ids"].update(right["scenario_ids"])
                    representative = max(left["records"], key=lambda item: len(item["finding_text"]))
                    left["tokens"] = representative["tokens"]
                    del clusters[right_index]
                    merged = True
                    break
            if merged:
                break

    unique_bugs = []
    for index, cluster in enumerate(clusters, 1):
        occurrences = cluster["records"]
        representative = max(occurrences, key=lambda item: len(item["finding_text"]))
        unique_bugs.append({
            "unique_id": f"UBUG-{index:03}",
            "scenario_id": representative.get("scenario_id"),
            "scenario_name": representative.get("scenario_name"),
            "module": representative.get("module"),
            "severity": _highest_severity(occurrences),
            "details": representative["finding_text"] or "Execution failed; see the source report logs for command-level details.",
            "occurrence_count": len(occurrences),
            "reports": sorted({item["report"] for item in occurrences}, key=str.casefold),
            "related_scenarios": sorted(
                {str(item.get("scenario_id", "")) for item in occurrences if item.get("scenario_id")},
                key=str.casefold,
            ),
            "sources": sorted(
                {source for item in occurrences for source in item.get("sources", [])}, key=str.casefold
            ),
        })

    result = {
        "generated_at": generated_at.isoformat(timespec="seconds"),
        "generated_at_display": generated_at.strftime("%d %b %Y, %I:%M:%S %p %Z"),
        "summary": {
            "source_reports": source_reports,
            "source_bugs": len(records),
            "unique_bugs": len(unique_bugs),
            "duplicates_removed": len(records) - len(unique_bugs),
        },
        "bugs": unique_bugs,
    }
    output = report_root / "Unique_Bug_Summary.json"
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result
