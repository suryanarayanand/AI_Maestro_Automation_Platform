from pathlib import Path


BUG_PATTERNS = [
    {
        "pattern": "Assertion failed",
        "type": "Assertion Failure",
        "severity": "Major"
    },
    {
        "pattern": "Element not found",
        "type": "UI Element Missing",
        "severity": "Major"
    },
    {
        "pattern": "Timeout",
        "type": "Timeout",
        "severity": "Major"
    },
    {
        "pattern": "Connection refused",
        "type": "Network Failure",
        "severity": "Critical"
    },
    {
        "pattern": "App crashed",
        "type": "Application Crash",
        "severity": "Critical"
    },
    {
        "pattern": "NoSuchElement",
        "type": "UI Element Missing",
        "severity": "Major"
    },
    {
        "pattern": "NullPointerException",
        "type": "Application Exception",
        "severity": "Critical"
    }
]


def parse_log(log_file):
    """
    Reads a Maestro log and identifies known failure patterns.
    """

    log_file = Path(log_file)

    if not log_file.exists():
        return {
            "bug_found": False,
            "bug_type": None,
            "severity": None,
            "matched_pattern": None,
            "reason": "Log file not found."
        }

    try:
        content = log_file.read_text(
            encoding="utf-8",
            errors="ignore"
        )

    except Exception as e:
        return {
            "bug_found": False,
            "bug_type": None,
            "severity": None,
            "matched_pattern": None,
            "reason": str(e)
        }

    content_lower = content.lower()

    for bug in BUG_PATTERNS:

        if bug["pattern"].lower() in content_lower:

            return {
                "bug_found": True,
                "bug_type": bug["type"],
                "severity": bug["severity"],
                "matched_pattern": bug["pattern"],
                "reason": bug["pattern"]
            }

    return {
        "bug_found": False,
        "bug_type": "Unknown Failure",
        "severity": "Major",
        "matched_pattern": None,
        "reason": "No known bug pattern matched."
    }