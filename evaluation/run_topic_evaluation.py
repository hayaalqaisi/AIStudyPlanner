import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from dotenv import load_dotenv

from evaluation.cases import TOPIC_EXTRACTION_CASES
from planner.ai.topic_extractor import TopicExtractionError, extract_topics
from planner.utils.performance import PerformanceMeasurement
from planner.utils.topic_evaluation import evaluate_topic_titles


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def evaluate_case(case, repetition):
    """Measure one extraction and compare it with fixed reference titles."""
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
        "performance": measurement.as_dict(),
    }


def build_summary(results):
    """Summarize all attempts, including failed extractions."""
    true_positives = sum(
        result["quality"]["true_positives"] for result in results
    )
    false_positives = sum(
        result["quality"]["false_positives"] for result in results
    )
    false_negatives = sum(
        result["quality"]["false_negatives"] for result in results
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
        "attempts": len(results),
        "successful_attempts": sum(
            result["outcome"] == "succeeded" for result in results
        ),
        "failed_attempts": sum(
            result["outcome"] == "failed" for result in results
        ),
        "micro_precision": precision,
        "micro_recall": recall,
        "micro_f1": f1,
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

    load_dotenv(PROJECT_ROOT / ".env")

    if (
        not os.getenv("OPENAI_API_KEY", "").strip()
        or not os.getenv("OPENAI_MODEL", "").strip()
    ):
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
                f"F1: {result['quality']['f1']:.3f}; "
                f"Duration: {result['performance']['duration_ms']} ms"
            )

    summary = build_summary(results)
    timestamp = datetime.now(timezone.utc)

    report = {
        "created_at": timestamp.isoformat(),
        "model": os.environ["OPENAI_MODEL"].strip(),
        "repetitions_per_case": args.repetitions,
        "notes": [
            "Cases are synthetic and references are predefined.",
            "Titles match after case and whitespace normalization.",
            "Equivalent wording may require manual semantic review.",
            "Failed extractions count as missing all expected topics.",
            "Latency covers extraction and validation, not report writing.",
            "RSS readings describe the entire local Python process.",
            "Memory readings are before/after samples, not peak usage.",
            "Requests run sequentially in the same process.",
        ],
        "summary": summary,
        "results": results,
    }

    output_directory = PROJECT_ROOT / "evaluation" / "results"
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