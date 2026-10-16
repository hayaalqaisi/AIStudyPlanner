import re
from collections import Counter
from datetime import date

from planner.ai.plan_review_proposal_validation import (
    ProposalValidationError,
    validate_explanation_claim,
    validate_review_proposal,
)


def evaluate_plan_review_proposal(case, options, proposal):
    """Score the decision, preference alignment, and final explanation."""
    sessions = case["sessions"]
    resume_date = case["resume_date"]

    has_unfinished_work = any(
        session["status"] in ("pending", "missed")
        for session in sessions
    )
    has_overdue_or_missed_work = any(
        session["status"] == "missed"
        or (
            session["status"] == "pending"
            and session["study_date"] < resume_date
        )
        for session in sessions
    )

    preference_check = case["preference_check"]

    if preference_check not in (
        None,
        "lowest_feasible_limit",
        "earliest_finish_lowest_limit",
    ):
        raise ValueError("The case has an unsupported preference check.")

    preference_applicable = preference_check is not None

    try:
        validated = validate_review_proposal(
            proposal,
            options=options,
            has_unfinished_work=has_unfinished_work,
            has_overdue_or_missed_work=has_overdue_or_missed_work,
        )
    except ProposalValidationError as error:
        return {
            "proposal_valid": False,
            "action_correct": False,
            "preference_applicable": preference_applicable,
            "preference_match": (
                False if preference_applicable else None
            ),
            "rubric_daily_minutes": None,
            "validation_error": str(error),
            "explanation_consistent": False,
            "explanation_error": (
                "No valid proposal is available for explanation scoring."
            ),
        }

    action_correct = validated["action"] == case["expected_action"]
    rubric_daily_minutes = None
    preference_match = None

    if preference_applicable:
        if not options:
            raise ValueError(
                "A preference-scored case must have feasible options."
            )

        if preference_check == "lowest_feasible_limit":
            rubric_daily_minutes = min(
                option["daily_study_minutes"]
                for option in options
            )
        else:
            earliest_finish = min(
                option["finish_date"]
                for option in options
            )
            rubric_daily_minutes = min(
                option["daily_study_minutes"]
                for option in options
                if option["finish_date"] == earliest_finish
            )

        preference_match = (
            action_correct
            and validated["action"] == "replan_unfinished_work"
            and validated["daily_study_minutes"] == rubric_daily_minutes
        )

    explanation_error = _check_explanation(
        case,
        options,
        validated,
        has_unfinished_work=has_unfinished_work,
    )

    return {
        "proposal_valid": True,
        "action_correct": action_correct,
        "preference_applicable": preference_applicable,
        "preference_match": preference_match,
        "rubric_daily_minutes": rubric_daily_minutes,
        "validation_error": "",
        "explanation_consistent": not explanation_error,
        "explanation_error": explanation_error,
    }


def _check_explanation(
    case,
    options,
    proposal,
    *,
    has_unfinished_work,
):
    """Check the factual claims emitted by the application's templates."""
    reason = proposal["reason"]
    current_minutes = case["current_daily_minutes"]
    selected_minutes = proposal["daily_study_minutes"]
    resume_date = case["resume_date"].isoformat()

    options_by_limit = {
        option["daily_study_minutes"]: option
        for option in options
    }
    current = options_by_limit.get(current_minutes)

    if proposal["action"] != "replan_unfinished_work":
        claim_type = "not_needed"
    elif selected_minutes == current_minutes:
        claim_type = "not_needed"
    elif current is not None:
        claim_type = "preference"
    else:
        claim_type = "required"

    try:
        validate_explanation_claim(
            proposal,
            limit_change_type=claim_type,
            current_daily_minutes=current_minutes,
            options=options,
        )
    except ProposalValidationError as error:
        return str(error)

    required_fragments = []
    expected_dates = []
    expected_numbers = []

    if proposal["action"] == "keep_current_plan":
        if has_unfinished_work:
            required_fragments = [
                "No missed or overdue work was identified",
                f"resume date of {resume_date}",
                "keep the current plan",
            ]
            expected_dates = [resume_date]
        else:
            required_fragments = [
                "No unfinished work remains",
                "without changing its daily limit",
            ]

    elif proposal["action"] == "cannot_fit":
        maximum = case["maximum_daily_minutes"]
        required_fragments = [
            "No server-validated replacement fits the unfinished work",
            f"from {resume_date}",
            f"limits of {current_minutes} to {maximum} minutes",
        ]
        expected_dates = [resume_date]
        expected_numbers = [current_minutes, maximum]

    else:
        selected = options_by_limit[selected_minutes]
        selected_finish = selected["finish_date"]

        if selected_minutes == current_minutes:
            required_fragments = [
                f"current {current_minutes} minutes per day",
                f"finishing on {selected_finish}",
                "No daily-limit increase is needed",
            ]
            expected_dates = [selected_finish]
            expected_numbers = [current_minutes]

        elif current is None:
            required_fragments = [
                "current daily limit has no feasible replacement",
                f"selected {selected_minutes} minutes per day",
                f"on {selected_finish}",
                "A higher daily limit is required",
            ]
            expected_dates = [selected_finish]
            expected_numbers = [selected_minutes]

        else:
            current_finish = current["finish_date"]
            days_saved = (
                date.fromisoformat(current_finish)
                - date.fromisoformat(selected_finish)
            ).days

            required_fragments = [
                f"current {current_minutes} minutes per day is feasible",
                f"finishing on {current_finish}",
                f"selected {selected_minutes} minutes per day",
                f"finishes on {selected_finish}",
                "increase is optional, rather than required for feasibility",
            ]
            expected_dates = [current_finish, selected_finish]
            expected_numbers = [current_minutes, selected_minutes]

            if days_saved > 0:
                unit = "day" if days_saved == 1 else "days"
                required_fragments.append(
                    f"{days_saved} {unit} earlier"
                )
                expected_numbers.append(days_saved)
            elif days_saved == 0:
                required_fragments.append("the same finish date")
            else:
                days_later = -days_saved
                unit = "day" if days_later == 1 else "days"
                required_fragments.append(
                    f"{days_later} {unit} later"
                )
                expected_numbers.append(days_later)

            if case["preference"] == "finish_sooner":
                if days_saved > 0:
                    required_fragments.append(
                        "consistent with your preference to finish sooner"
                    )
                else:
                    required_fragments.append(
                        "provides no earlier finish"
                    )
            else:
                required_fragments.append(
                    "current-limit option also remains available "
                    "with a lower daily limit"
                )

    normalized_reason = " ".join(reason.casefold().split())

    for fragment in required_fragments:
        if fragment.casefold() not in normalized_reason:
            return f"Missing or incorrect factual statement: {fragment}"

    actual_dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", reason)

    if Counter(actual_dates) != Counter(expected_dates):
        return "The explanation contains missing or unexpected dates."

    reason_without_dates = re.sub(
        r"\b\d{4}-\d{2}-\d{2}\b",
        "",
        reason,
    )
    actual_numbers = re.findall(r"\b\d+\b", reason_without_dates)

    if Counter(actual_numbers) != Counter(
        str(number) for number in expected_numbers
    ):
        return "The explanation contains missing or unexpected numbers."

    return ""