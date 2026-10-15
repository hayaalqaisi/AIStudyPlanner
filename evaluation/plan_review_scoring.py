from planner.ai.plan_review_proposal_validation import (
    ProposalValidationError,
    validate_review_proposal,
)


def evaluate_plan_review_proposal(case, options, proposal):
    """Score a proposal against safety rules and a scenario's rubric."""
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
        }

    action_correct = (
        validated["action"] == case["expected_action"]
    )

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

    return {
        "proposal_valid": True,
        "action_correct": action_correct,
        "preference_applicable": preference_applicable,
        "preference_match": preference_match,
        "rubric_daily_minutes": rubric_daily_minutes,
        "validation_error": "",
    }