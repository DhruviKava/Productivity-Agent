def score_quality(text):
    # placeholder: simple heuristics
    if not text:
        return 0
    words = len(text.split())
    score = min(100, 20 + words//5)
    return score
