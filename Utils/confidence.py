def calculate_confidence(maestro, ai, visual):
    """
    Calculate confidence based on available evidence.
    """

    score = 0

    if maestro:
        score += 60

    if ai:
        score += 25

    if visual:
        score += 15

    return min(score, 100)