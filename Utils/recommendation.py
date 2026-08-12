def get_recommendation(bug_type):
    """
    Returns a recommendation based on the bug type.
    """

    recommendations = {

        "Application Crash":
            "Check application crash logs, stack trace, and recent code changes.",

        "Application Exception":
            "Review exception logs and fix the underlying application error.",

        "Assertion Failure":
            "Verify the expected UI element, text, or application behavior.",

        "UI Element Missing":
            "Verify the UI locator, screen rendering, and application state.",

        "Timeout":
            "Check backend response time, increase timeout if appropriate, and verify network latency.",

        "Network Failure":
            "Verify API availability, internet connection, and server status.",

        "Login Failure":
            "Verify login credentials, authentication service, and login API.",

        "Blank Screen":
            "Check page rendering, API response, and application initialization.",

        "Visual Difference":
            "Review baseline images and determine whether the UI change is expected.",

        "Text Mismatch":
            "Verify displayed text against functional requirements.",

        "Alignment Issue":
            "Review UI layout and responsive design.",

        "Unknown Failure":
            "Review Maestro logs, screenshots, AI analysis, and visual comparison."
    }

    return recommendations.get(
        bug_type,
        "Review execution logs and screenshots."
    )