ACTION_MAP = {
    "open": "tapOn",
    "tap": "tapOn",
    "click": "tapOn",
    "select": "tapOn",
    "choose": "tapOn",

    "enter": "inputText",
    "type": "inputText",

    "scroll": "swipe",
    "swipe": "swipe",

    "verify": "assertVisible",
    "assert": "assertVisible",

    "wait": "extendedWaitUntil"
}

INTENT_ACTION_MAP = {
    "ASSERT_VISIBLE": "assertVisible",
    "ASSERT_NOT_VISIBLE": "assertNotVisible",
    "TAP": "tapOn",
}
def parse_step(step: str):
    """
    Converts an English test step into:
    - action
    - target
    """

    import re

    intent = re.fullmatch(r"\s*([A-Z_]+)\s*\(\s*([^)]+?)\s*\)\s*", step)
    if intent and intent.group(1) in INTENT_ACTION_MAP:
        return {
            "action": INTENT_ACTION_MAP[intent.group(1)],
            "target": intent.group(2),
            "explicit_locator": True,
        }

    words = step.strip().split()

    if not words:
        return None

    lowered = " ".join(words).lower()
    if lowered.startswith("take screenshot "):
        return {
            "action": "takeScreenshot",
            "target": " ".join(words[2:]),
        }
    if lowered.startswith("capture screenshot "):
        return {
            "action": "takeScreenshot",
            "target": " ".join(words[2:]),
        }

    action_word = words[0].lower()

    action = ACTION_MAP.get(action_word)

    target = " ".join(words[1:])

    # Remove common filler words
    filler = [
        "the",
        "on",
        "to",
        "tab",
        "button",
        "page",
        "screen"
    ]

    target_words = [
        w for w in target.split()
        if w.lower() not in filler
    ]

    target = " ".join(target_words)

    return {
        "action": action,
        "target": target
    }

if __name__ == "__main__":

    tests = [

        "Open Videos tab",

        "Tap on Home",

        "Click Account",

        "Select Photos",

        "Verify Login",

        "Scroll down",

        "Enter Email"

    ]

    for step in tests:
        print(step)
        print(parse_step(step))
        print("-" * 40)
