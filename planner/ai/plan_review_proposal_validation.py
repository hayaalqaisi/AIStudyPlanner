import re


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


def validate_explanation_claim(
    proposal,
    *,
    limit_change_type,
    current_daily_minutes,
    options,
):
    """Check explanation claims after the proposal decision is validated."""
    if limit_change_type not in (
        "not_needed",
        "preference",
        "required",
    ):
        raise ProposalValidationError(
            "The explanation has an unsupported limit change type."
        )

    current_feasible = any(
        option["daily_study_minutes"] == current_daily_minutes
        for option in options
    )

    if proposal["action"] == "replan_unfinished_work":
        selected_minutes = proposal["daily_study_minutes"]

        if selected_minutes == current_daily_minutes:
            expected_type = "not_needed"
        elif current_feasible:
            expected_type = "preference"
        else:
            expected_type = "required"
    else:
        expected_type = "not_needed"

    if limit_change_type != expected_type:
        if limit_change_type == "required" and current_feasible:
            raise ProposalValidationError(
                "The current daily limit is feasible; "
                "an increase cannot be described as required."
            )

        raise ProposalValidationError(
            "The explanation's limit change type contradicts "
            f"the scheduling facts. Expected '{expected_type}'."
        )

    if (
        proposal["action"] == "replan_unfinished_work"
        and current_feasible
    ):
        normalized_reason = " ".join(
            proposal["reason"].casefold().replace("\u2019", "'").split()
        )

        unsupported_capacity_claim = re.search(
            r"\b(?:cannot|can't|insufficient|not enough|"
            r"won't meet|unable)\b",
            normalized_reason,
        )

        if unsupported_capacity_claim:
            raise ProposalValidationError(
                "The current daily limit is feasible. "
                "Rewrite the explanation without claiming "
                "that it cannot accommodate the unfinished work."
            )

    return limit_change_type