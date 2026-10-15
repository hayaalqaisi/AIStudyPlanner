import argparse
import json
import os
from datetime import datetime, timezone
from statistics import mean

import django
from django.conf import settings

from evaluation.plan_review_cases import PLAN_REVIEW_CASES
from evaluation.plan_review_scoring import evaluate_plan_review_proposal
from planner.ai.plan_review_proposal_agent import (
    ProposalGenerationError,
    propose_plan_review,
)
from planner.services.plan_review_options_service import build_review_options
from planner.utils.performance import PerformanceMeasurement


def summarize_progress(sessions, resume_date):
    """Calculate numeric progress for a synthetic evaluation scenario."""
    progress = {
        "completed_minutes": 0,
        "pending_minutes": 0,
        "missed_minutes": 0,
        "overdue_pending_minutes": 0,
    }

    for session in sessions:
        minutes = session["duration_minutes"]
        status = session["status"]

        if status == "completed":
            progress["completed_minutes"] += minutes
        elif status == "missed":
            progress["missed_minutes"] += minutes
        elif status == "pending":
            progress["pending_minutes"] += minutes

            if session["study_date"] < resume_date:
                progress["overdue_pending_minutes"] += minutes

    return progress


def evaluate_case(case, repetition):
    """Evaluate one agent recommendation without accessing the database."""
    options = build_review_options(
        case["sessions"],
        case["resume_date"],
        case["current_daily_minutes"],
        case["maximum_daily_minutes"],
    )
    progress = summarize_progress(
        case["sessions"],
        case["resume_date"],
    )

    proposal = None
    outcome = "succeeded"
    error_message = ""

    with PerformanceMeasurement() as measurement:
        try:
            proposal = propose_plan_review(
                progress=progress,
                options=options,
                preference=case["preference"],
                current_daily_minutes=case["current_daily_minutes"],
                maximum_daily_minutes=case["maximum_daily_minutes"],
                resume_date=case["resume_date"],
            )
        except ProposalGenerationError as error:
            outcome = "failed"
            error_message = str(error)

    quality = evaluate_plan_review_proposal(
        case,
        options,
        proposal,
    )

    return {
        "case": case["name"],
        "repetition": repetition,
        "outcome": outcome,
        "error_message": error_message,
        "resume_date": case["resume_date"].isoformat(),
        "current_daily_minutes": case["current_daily_minutes"],
        "maximum_daily_minutes": case["maximum_daily_minutes"],
        "preference": case["preference"],
        "expected_action": case["expected_action"],
        "preference_check": case["preference_check"],
        "progress": progress,
        "feasible_options": options,
        "proposal": proposal,
        "quality": quality,
        "performance": measurement.as_dict(),
    }


def build_summary(results):
    """Include failed attempts in the relevant score denominators."""
    if not results:
        raise ValueError("Provide at least one evaluation result.")

    attempts = len(results)
    preference_results = [
        result
        for result in results
        if result["quality"]["preference_applicable"]
    ]

    accepted_proposals = sum(
        result["quality"]["proposal_valid"]
        for result in results
    )
    correct_actions = sum(
        result["quality"]["action_correct"]
        for result in results
    )
    preference_matches = sum(
        result["quality"]["preference_match"] is True
        for result in preference_results
    )

    return {
        "attempts": attempts,
        "successful_attempts": sum(
            result["outcome"] == "succeeded"
            for result in results
        ),
        "failed_attempts": sum(
            result["outcome"] == "failed"
            for result in results
        ),
        "accepted_proposals": accepted_proposals,
        "accepted_proposal_rate": accepted_proposals / attempts,
        "correct_actions": correct_actions,
        "action_accuracy_all_attempts": correct_actions / attempts,
        "preference_applicable_attempts": len(preference_results),
        "preference_matches": preference_matches,
        "preference_alignment": (
            preference_matches / len(preference_results)
            if preference_results
            else None
        ),
        "average_duration_ms": mean(
            result["performance"]["duration_ms"]
            for result in results
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
        description="Evaluate AI study-plan review proposals."
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
        for case in PLAN_REVIEW_CASES:
            print(
                f"Evaluating {case['name']} "
                f"(repetition {repetition}/{args.repetitions})..."
            )

            result = evaluate_case(case, repetition)
            results.append(result)
            quality = result["quality"]

            print(
                f"  Outcome: {result['outcome']}; "
                f"Valid: {quality['proposal_valid']}; "
                f"Action correct: {quality['action_correct']}; "
                f"Preference match: {quality['preference_match']}; "
                f"Duration: {result['performance']['duration_ms']} ms"
            )

    summary = build_summary(results)
    timestamp = datetime.now(timezone.utc)

    report = {
        "report_version": 1,
        "created_at": timestamp.isoformat(),
        "model": settings.OPENAI_MODEL,
        "case_count": len(PLAN_REVIEW_CASES),
        "repetitions_per_case": args.repetitions,
        "notes": [
            "Scenarios are synthetic and expected actions are predefined.",
            "Feasible options are calculated by the application scheduler.",
            "No study plans or application records are changed.",
            "The application validates AI proposals before returning them.",
            "Rejected proposals appear as failed attempts.",
            "Raw rejected model outputs are not captured by this runner.",
            "Accepted-proposal rate is not a raw model safety measurement.",
            "Action accuracy includes all attempts, including failures.",
            "Preference alignment includes all preference-applicable attempts.",
            "Preference checks are benchmark rubrics, not universal optima.",
            "Lighter-workload cases prefer the lowest feasible daily limit.",
            "Finish-sooner cases prefer the earliest finish, then lowest limit.",
            "Explanations require manual factual and qualitative review.",
            "Latency covers proposal generation and application validation.",
            "Option generation and evaluation scoring are outside latency.",
            "Memory readings describe the entire local Python process.",
            "Memory readings are before/after samples, not peak usage.",
            "Requests run sequentially in the same process.",
        ],
        "summary": summary,
        "results": results,
    }

    output_directory = settings.BASE_DIR / "evaluation" / "results"
    output_directory.mkdir(parents=True, exist_ok=True)

    output_path = output_directory / (
        f"plan_review_evaluation_"
        f"{timestamp.strftime('%Y%m%dT%H%M%S%fZ')}.json"
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