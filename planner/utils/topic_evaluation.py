from difflib import SequenceMatcher


def evaluate_topic_titles(expected_titles, predicted_titles):
    """
    Compare titles after normalizing capitalization and whitespace.

    Duplicate predictions count as extra incorrect predictions.
    This measures title matching, not semantic equivalence.
    """
    expected, predicted = _prepare_titles(
        expected_titles,
        predicted_titles,
    )

    true_positives = len(set(expected) & set(predicted))

    return _calculate_metrics(
        len(expected),
        len(predicted),
        true_positives,
    )


def evaluate_topic_titles_fuzzy(
    expected_titles,
    predicted_titles,
    *,
    threshold=0.85,
):
    """
    Compare titles using one-to-one character-similarity matches.

    Find the largest number of matches meeting the threshold.
    Duplicate normalized predictions can match only once.

    This measures wording similarity, not semantic equivalence.
    """
    if (
        type(threshold) not in (int, float)
        or not 0 < threshold <= 1
    ):
        raise ValueError(
            "The similarity threshold must be greater than 0 "
            "and at most 1."
        )

    expected, predicted = _prepare_titles(
        expected_titles,
        predicted_titles,
    )

    unique_predictions = list(dict.fromkeys(predicted))

    similarities = [
        [
            SequenceMatcher(
                None,
                prediction,
                reference,
                autojunk=False,
            ).ratio()
            for reference in expected
        ]
        for prediction in unique_predictions
    ]

    candidates = [
        sorted(
            [
                reference_index
                for reference_index, score in enumerate(scores)
                if score >= threshold
            ],
            key=lambda reference_index: (
                -scores[reference_index],
                reference_index,
            ),
        )
        for scores in similarities
    ]

    matched_references = {}

    def assign_prediction(prediction_index, visited_references):
        for reference_index in candidates[prediction_index]:
            if reference_index in visited_references:
                continue

            visited_references.add(reference_index)
            previous_prediction = matched_references.get(
                reference_index
            )

            if (
                previous_prediction is None
                or assign_prediction(
                    previous_prediction,
                    visited_references,
                )
            ):
                matched_references[reference_index] = prediction_index
                return True

        return False

    for prediction_index in range(len(unique_predictions)):
        assign_prediction(prediction_index, set())

    matches = [
        {
            "expected_title": expected[reference_index],
            "predicted_title": unique_predictions[prediction_index],
            "similarity": similarities[prediction_index][reference_index],
        }
        for reference_index, prediction_index in sorted(
            matched_references.items()
        )
    ]

    return {
        **_calculate_metrics(
            len(expected),
            len(predicted),
            len(matches),
        ),
        "threshold": threshold,
        "matches": matches,
    }


def _calculate_metrics(expected_count, predicted_count, true_positives):
    false_positives = predicted_count - true_positives
    false_negatives = expected_count - true_positives

    precision = (
        true_positives / predicted_count
        if predicted_count
        else 0.0
    )
    recall = true_positives / expected_count

    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall > 0
        else 0.0
    )

    return {
        "expected_count": expected_count,
        "predicted_count": predicted_count,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def _prepare_titles(expected_titles, predicted_titles):
    expected = _normalize_titles(expected_titles)
    predicted = _normalize_titles(predicted_titles)

    if not expected:
        raise ValueError("Provide at least one expected topic title.")

    if len(expected) != len(set(expected)):
        raise ValueError("Expected topic titles must be unique.")

    return expected, predicted


def _normalize_titles(titles):
    """Normalize case and whitespace without changing topic meaning."""
    if not isinstance(titles, (list, tuple)):
        raise ValueError(
            "Topic titles must be supplied as a list or tuple."
        )

    normalized = []

    for title in titles:
        if not isinstance(title, str) or not title.strip():
            raise ValueError("Each topic title must contain text.")

        normalized.append(" ".join(title.split()).casefold())

    return normalized