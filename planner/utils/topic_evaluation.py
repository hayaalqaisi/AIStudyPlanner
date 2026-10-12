def evaluate_topic_titles(expected_titles, predicted_titles):
    """
    Compare topic titles using exact matches after normalizing
    capitalization and whitespace.

    Duplicate predictions count as extra incorrect predictions.
    This measures title matching, not semantic equivalence.
    """
    expected = _normalize_titles(expected_titles)
    predicted = _normalize_titles(predicted_titles)

    if not expected:
        raise ValueError("Provide at least one expected topic title.")

    if len(expected) != len(set(expected)):
        raise ValueError("Expected topic titles must be unique.")

    expected_set = set(expected)
    predicted_set = set(predicted)

    true_positives = len(expected_set & predicted_set)
    false_positives = len(predicted) - true_positives
    false_negatives = len(expected_set - predicted_set)

    precision = (
        true_positives / len(predicted)
        if predicted
        else 0.0
    )
    recall = true_positives / len(expected)

    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall > 0
        else 0.0
    )

    return {
        "expected_count": len(expected),
        "predicted_count": len(predicted),
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def _normalize_titles(titles):
    """Normalize case and whitespace without changing topic meaning."""
    if not isinstance(titles, (list, tuple)):
        raise ValueError("Topic titles must be supplied as a list or tuple.")

    normalized = []

    for title in titles:
        if not isinstance(title, str) or not title.strip():
            raise ValueError("Each topic title must contain text.")

        normalized.append(" ".join(title.split()).casefold())

    return normalized