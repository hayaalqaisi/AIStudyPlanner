import argparse
import json
import os
from datetime import datetime, timezone
from statistics import mean

import django
from django.conf import settings

from evaluation.cases import TOPIC_EXTRACTION_CASES
from planner.ai.topic_extractor import TopicExtractionError, extract_topics
from planner.utils.performance import PerformanceMeasurement
from planner.utils.topic_evaluation import (
    evaluate_topic_titles,
    evaluate_topic_titles_fuzzy,
)


FUZZY_THRESHOLD = 0.85


def evaluate_case(case, repetition):
    """Measure extraction and calculate exact and fuzzy title scores."""
    predicted_titles = []
    outcome = "succeeded"
    error_message = ""

    with PerformanceMeasurement() as measurement:
        try:
            topics = extract_topics(case["syllabus_text"])
            predicted_titles = [topic["title"] for topic in topics]
        except TopicExtractionError as error:
            outcome = "failed"
            error_message = str(error)

    return {
        "case": case["name"],
        "repetition": repetition,
        "outcome": outcome,
        "error_message": error_message,
        "expected_titles": case["expected_titles"],
        "predicted_titles": predicted_titles,
        "quality": evaluate_topic_titles(
            case["expected_titles"],
            predicted_titles,
        ),
        "quality_fuzzy": evaluate_topic_titles_fuzzy(
            case["expected_titles"],
            predicted_titles,
            threshold=FUZZY_THRESHOLD,
        ),
        "performance": measurement.as_dict(),
    }


def _micro_scores(results, quality_field):
    """Aggregate matching counts before calculating overall scores."""
    true_positives = sum(
        result[quality_field]["true_positives"]
        for result in results
    )
    false_positives = sum(
        result[quality_field]["false_positives"]
        for result in results
    )
    false_negatives = sum(
        result[quality_field]["false_negatives"]
        for result in results
    )

    precision = (
        true_positives / (true_positives + false_positives)
        if true_positives + false_positives
        else 0.0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if true_positives + false_negatives
        else 0.0
    )
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )

    return {
        "micro_precision": precision,
        "micro_recall": recall,
        "micro_f1": f1,
    }


def build_summary(results):
    """Summarize all attempts, including failed extractions."""
    if not results:
        raise ValueError("Provide at least one evaluation result.")

    exact = _micro_scores(results, "quality")
    fuzzy = _micro_scores(results, "quality_fuzzy")

    return {
        "attempts": len(results),
        "successful_attempts": sum(
            result["outcome"] == "succeeded" for result in results
        ),
        "failed_attempts": sum(
            result["outcome"] == "failed" for result in results
        ),
        **exact,
        "fuzzy_threshold": FUZZY_THRESHOLD,
        "fuzzy_micro_precision": fuzzy["micro_precision"],
        "fuzzy_micro_recall": fuzzy["micro_recall"],
        "fuzzy_micro_f1": fuzzy["micro_f1"],
        "average_duration_ms": mean(
            result["performance"]["duration_ms"] for result in results
        ),
        "average_memory_after_bytes": mean(
            result["performance"]["memory_after_bytes"]
            for result in results
        ),
        "average_memory_delta_bytes": mean(
            result["performance"]["memory_delta_bytes"]
            for result in results
        ),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate syllabus topic extraction."
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        default=1,
        choices=range(1, 11),
        metavar="1-10",
        help="Attempts per case. Each attempt makes an OpenAI request.",
    )
    args = parser.parse_args()

    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        "study_planner.settings",
    )
    django.setup()

    if not settings.OPENAI_API_KEY or not settings.OPENAI_MODEL:
        parser.error(
            "Configure OPENAI_API_KEY and OPENAI_MODEL in your local .env."
        )

    results = []

    for repetition in range(1, args.repetitions + 1):
        for case in TOPIC_EXTRACTION_CASES:
            print(
                f"Evaluating {case['name']} "
                f"(repetition {repetition}/{args.repetitions})..."
            )
            result = evaluate_case(case, repetition)
            results.append(result)

            print(
                f"  Outcome: {result['outcome']}; "
                f"Exact F1: {result['quality']['f1']:.3f}; "
                f"Fuzzy F1: {result['quality_fuzzy']['f1']:.3f}; "
                f"Duration: {result['performance']['duration_ms']} ms"
            )

    summary = build_summary(results)
    timestamp = datetime.now(timezone.utc)

    report = {
        "report_version": 2,
        "created_at": timestamp.isoformat(),
        "model": settings.OPENAI_MODEL,
        "case_count": len(TOPIC_EXTRACTION_CASES),
        "repetitions_per_case": args.repetitions,
        "notes": [
            "Cases are synthetic and references are predefined.",
            "Cases include baseline and longer structured syllabi.",
            "Exact matching normalizes case and whitespace.",
            "Fuzzy matching uses character similarity, not semantics.",
            "Fuzzy matching uses one-to-one title assignments.",
            "Duplicate predictions count against precision.",
            "The fuzzy threshold is fixed at 0.85.",
            "Inspect matched title pairs before interpreting fuzzy scores.",
            "Failed extractions count as missing all expected topics.",
            "Latency covers extraction and validation, not scoring.",
            "RSS readings describe the entire local Python process.",
            "Memory readings are before/after samples, not peak usage.",
            "Requests run sequentially in the same process.",
            "This report evaluates topics, not plan-review recommendations.",
        ],
        "summary": summary,
        "results": results,
    }

    output_directory = settings.BASE_DIR / "evaluation" / "results"
    output_directory.mkdir(parents=True, exist_ok=True)

    output_path = output_directory / (
        f"topic_evaluation_{timestamp.strftime('%Y%m%dT%H%M%S%fZ')}.json"
    )
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\nSummary:")
    print(json.dumps(summary, indent=2))
    print(f"\nResults saved to: {output_path}")

    return 1 if summary["failed_attempts"] else 0


if __name__ == "__main__":
    raise SystemExit(main())