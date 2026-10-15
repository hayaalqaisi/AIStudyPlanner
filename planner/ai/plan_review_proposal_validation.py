class ProposalValidationError(Exception):
    """An invalid AI proposal that must not be applied."""


def validate_review_proposal(
    proposal,
    *,
    options,
    has_unfinished_work,
    has_overdue_or_missed_work,
):
    """Validate a proposal against server-calculated scheduling options."""
    required_fields = {
        "action",
        "daily_study_minutes",
        "reason",
    }

    if (
        not isinstance(proposal, dict)
        or set(proposal) != required_fields
    ):
        raise ProposalValidationError(
            "The proposal has an invalid format."
        )

    action = proposal["action"]
    daily_minutes = proposal["daily_study_minutes"]
    reason = proposal["reason"]

    if action not in (
        "keep_current_plan",
        "replan_unfinished_work",
        "cannot_fit",
    ):
        raise ProposalValidationError(
            "The agent selected an unsupported action."
        )

    if (
        not isinstance(reason, str)
        or not 1 <= len(reason.strip()) <= 1000
    ):
        raise ProposalValidationError(
            "The agent returned an invalid explanation."
        )

    if action == "keep_current_plan":
        if daily_minutes is not None:
            raise ProposalValidationError(
                "Keeping a plan must not change its daily limit."
            )

        if has_overdue_or_missed_work:
            raise ProposalValidationError(
                "The current schedule contains missed or overdue work. "
                "It cannot be presented as an unchanged valid schedule."
            )

    elif action == "replan_unfinished_work":
        if not has_unfinished_work:
            raise ProposalValidationError(
                "There is no unfinished work to reschedule."
            )

        allowed_limits = {
            option["daily_study_minutes"]
            for option in options
        }

        if (
            type(daily_minutes) is not int
            or daily_minutes not in allowed_limits
        ):
            raise ProposalValidationError(
                "The proposed daily limit is not one of "
                "the server-validated scheduling options."
            )

    else:
        if daily_minutes is not None:
            raise ProposalValidationError(
                "An infeasible proposal must not specify a daily limit."
            )

        if not has_unfinished_work or options:
            raise ProposalValidationError(
                "The agent reported that work cannot fit, "
                "but the scheduling evidence does not support that."
            )

    return {
        "action": action,
        "daily_study_minutes": daily_minutes,
        "reason": reason.strip(),
    }