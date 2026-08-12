def get_severity(bug_type):
    """
    Returns severity based on bug type.
    """

    severity_map = {

        # Critical Bugs
        "Application Crash": "Critical",
        "Blank Screen": "Critical",
        "Login Failure": "Critical",
        "Network Failure": "Critical",
        "Application Exception": "Critical",

        # Major Bugs
        "Assertion Failure": "Major",
        "UI Element Missing": "Major",
        "Timeout": "Major",
        "API Failure": "Major",

        # Minor Bugs
        "Visual Difference": "Minor",
        "Text Mismatch": "Minor",
        "Alignment Issue": "Minor",

        # Default
        "Unknown Failure": "Major"
    }

    return severity_map.get(bug_type, "Major")