import json
from datetime import date

from planner.ai.openai_client import AIServiceError, call_openai
from planner.ai.plan_review_proposal_tools import (
    PLAN_REVIEW_PROPOSAL_TOOLS,
)
from planner.ai.plan_review_proposal_validation import (
    ProposalValidationError,
    validate_explanation_claim,
    validate_review_proposal,
)
from planner.ai.prompt_loader import load_prompt


class ProposalGenerationError(Exception):
    """An AI proposal failure suitable for displaying to the student."""


def propose_plan_review(
    *,
    progress,
    options,
    preference,
    current_daily_minutes,
    maximum_daily_minutes,
    resume_date,
):
    """Return an AI-selected decision with a code-generated explanation."""
    required_progress_fields = {
        "completed_minutes",
        "pending_minutes",
        "missed_minutes",
        "overdue_pending_minutes",
    }

    if (
        not isinstance(progress, dict)
        or set(progress) != required_progress_fields
    ):
        raise ProposalGenerationError(
            "The progress summary has an invalid format."
        )

    if any(
        type(value) is not int or value < 0
        for value in progress.values()
    ):
        raise ProposalGenerationError(
            "Progress totals must be nonnegative whole numbers."
        )

    if progress["overdue_pending_minutes"] > progress["pending_minutes"]:
        raise ProposalGenerationError(
            "The overdue work total is invalid."
        )

    if preference not in ("manageable_workload", "finish_sooner"):
        raise ProposalGenerationError(
            "Choose a supported study preference."
        )

    if (
        type(current_daily_minutes) is not int
        or type(maximum_daily_minutes) is not int
        or not 15 <= current_daily_minutes <= maximum_daily_minutes <= 720
    ):
        raise ProposalGenerationError(
            "The daily study limits are invalid."
        )

    if type(resume_date) is not date:
        raise ProposalGenerationError("Choose a valid resume date.")

    if not isinstance(options, list):
        raise ProposalGenerationError(
            "The scheduling options have an invalid format."
        )

    finish_dates = {}

    for option in options:
        if (
            not isinstance(option, dict)
            or type(option.get("daily_study_minutes")) is not int
            or not current_daily_minutes
            <= option["daily_study_minutes"]
            <= maximum_daily_minutes
        ):
            raise ProposalGenerationError(
                "A scheduling option has an invalid daily limit."
            )

        daily_minutes = option["daily_study_minutes"]

        if daily_minutes in finish_dates:
            raise ProposalGenerationError(
                "The scheduling options contain duplicate daily limits."
            )

        finish_date = option.get("finish_date")

        if not isinstance(finish_date, str):
            raise ProposalGenerationError(
                "A scheduling option has an invalid finish date."
            )

        try:
            parsed_finish_date = date.fromisoformat(finish_date)
        except ValueError:
            raise ProposalGenerationError(
                "A scheduling option has an invalid finish date."
            ) from None

        if parsed_finish_date < resume_date:
            raise ProposalGenerationError(
                "A scheduling option finishes before the resume date."
            )

        finish_dates[daily_minutes] = parsed_finish_date

    current_finish_date = finish_dates.get(current_daily_minutes)
    earliest_finish_date = min(finish_dates.values(), default=None)

    facts = {
        "has_unfinished_work": (
            progress["pending_minutes"] + progress["missed_minutes"] > 0
        ),
        "current_limit_is_feasible": current_finish_date is not None,
        "current_limit_finish_date": (
            current_finish_date.isoformat()
            if current_finish_date is not None
            else None
        ),
        "earliest_finish_date": (
            earliest_finish_date.isoformat()
            if earliest_finish_date is not None
            else None
        ),
        "option_comparisons": [
            {
                "daily_study_minutes": option["daily_study_minutes"],
                "finish_date": option["finish_date"],
                "days_earlier_than_current": (
                    (
                        current_finish_date
                        - finish_dates[option["daily_study_minutes"]]
                    ).days
                    if current_finish_date is not None
                    else None
                ),
            }
            for option in options
        ],
    }

    context = {
        "progress": progress,
        "feasible_options": options,
        "preference": preference,
        "current_daily_minutes": current_daily_minutes,
        "maximum_daily_minutes": maximum_daily_minutes,
        "resume_date": resume_date.isoformat(),
        "facts": facts,
    }

    try:
        instructions = load_prompt("plan_review.md")
    except AIServiceError as error:
        raise ProposalGenerationError(str(error)) from None

    proposal = _request_proposal(instructions, context)

    has_overdue_or_missed_work = (
        progress["overdue_pending_minutes"] > 0
        or progress["missed_minutes"] > 0
    )

    validated = _validate_decision(
        proposal,
        options=options,
        has_unfinished_work=facts["has_unfinished_work"],
        has_overdue_or_missed_work=has_overdue_or_missed_work,
    )

    try:
        validate_explanation_claim(
            validated,
            limit_change_type=proposal["limit_change_type"],
            current_daily_minutes=current_daily_minutes,
            options=options,
        )
    except ProposalValidationError as error:
        explanation_error = str(error)
    else:
        return _with_factual_reason(
            validated,
            progress=progress,
            current_daily_minutes=current_daily_minutes,
            finish_dates=finish_dates,
            maximum_daily_minutes=maximum_daily_minutes,
            resume_date=resume_date,
            preference=preference,
        )

    retry_context = {
        **context,
        "explanation_repair": {
            "validation_error": explanation_error,
            "previous_proposal": proposal,
            "required_action": validated["action"],
            "required_daily_study_minutes": (
                validated["daily_study_minutes"]
            ),
        },
    }

    retry_instructions = (
        instructions
        + "\n\nEXPLANATION REPAIR:\n"
        "The previous decision passed scheduling validation, but its "
        "explanation failed validation. Correct limit_change_type and "
        "reason using the supplied facts and validation_error. "
        "Keep required_action and required_daily_study_minutes exactly "
        "unchanged. Submit the complete proposal using the same tool."
    )

    try:
        retry_proposal = _request_proposal(
            retry_instructions,
            retry_context,
        )

        repaired = _validate_decision(
            retry_proposal,
            options=options,
            has_unfinished_work=facts["has_unfinished_work"],
            has_overdue_or_missed_work=has_overdue_or_missed_work,
        )

        if (
            repaired["action"] != validated["action"]
            or repaired["daily_study_minutes"]
            != validated["daily_study_minutes"]
        ):
            raise ProposalGenerationError(
                "The explanation retry changed the validated decision."
            )

        validate_explanation_claim(
            repaired,
            limit_change_type=retry_proposal["limit_change_type"],
            current_daily_minutes=current_daily_minutes,
            options=options,
        )
    except (ProposalGenerationError, ProposalValidationError):
        pass
    else:
        validated = repaired

    return _with_factual_reason(
        validated,
        progress=progress,
        current_daily_minutes=current_daily_minutes,
        finish_dates=finish_dates,
        maximum_daily_minutes=maximum_daily_minutes,
        resume_date=resume_date,
        preference=preference,
    )


def _request_proposal(instructions, context):
    """Request and parse exactly one structured proposal."""
    try:
        response = call_openai(
            instructions=instructions,
            input=json.dumps(context),
            tools=PLAN_REVIEW_PROPOSAL_TOOLS,
            tool_choice={
                "type": "function",
                "name": "submit_review_proposal",
            },
            parallel_tool_calls=False,
            max_output_tokens=1000,
        )
    except AIServiceError as error:
        raise ProposalGenerationError(str(error)) from None

    if response.status != "completed":
        raise ProposalGenerationError(
            "The agent did not complete its proposal."
        )

    calls = [
        item
        for item in response.output
        if item.type == "function_call"
    ]

    if (
        len(calls) != 1
        or calls[0].name != "submit_review_proposal"
    ):
        raise ProposalGenerationError(
            "The agent must submit exactly one review proposal."
        )

    try:
        proposal = json.loads(calls[0].arguments)
    except (json.JSONDecodeError, TypeError):
        raise ProposalGenerationError(
            "The agent returned unreadable proposal arguments."
        ) from None

    required_fields = {
        "action",
        "daily_study_minutes",
        "limit_change_type",
        "reason",
    }

    if (
        not isinstance(proposal, dict)
        or set(proposal) != required_fields
    ):
        raise ProposalGenerationError(
            "The proposal has an invalid format."
        )

    return proposal


def _validate_decision(
    proposal,
    *,
    options,
    has_unfinished_work,
    has_overdue_or_missed_work,
):
    """Validate the proposal format used by approval services."""
    try:
        return validate_review_proposal(
            {
                "action": proposal["action"],
                "daily_study_minutes": proposal["daily_study_minutes"],
                "reason": proposal["reason"],
            },
            options=options,
            has_unfinished_work=has_unfinished_work,
            has_overdue_or_missed_work=has_overdue_or_missed_work,
        )
    except ProposalValidationError as error:
        raise ProposalGenerationError(str(error)) from None


def _with_factual_reason(
    proposal,
    *,
    progress,
    current_daily_minutes,
    finish_dates,
    maximum_daily_minutes,
    resume_date,
    preference,
):
    """Replace model prose with the explanation used throughout the app."""
    return {
        **proposal,
        "reason": _build_factual_reason(
            proposal,
            progress=progress,
            current_daily_minutes=current_daily_minutes,
            finish_dates=finish_dates,
            maximum_daily_minutes=maximum_daily_minutes,
            resume_date=resume_date,
            preference=preference,
        ),
    }


def _build_factual_reason(
    proposal,
    *,
    progress,
    current_daily_minutes,
    finish_dates,
    maximum_daily_minutes,
    resume_date,
    preference,
):
    """Explain a validated choice using calculated facts."""
    if proposal["action"] == "keep_current_plan":
        unfinished_minutes = (
            progress["pending_minutes"] + progress["missed_minutes"]
        )

        if unfinished_minutes == 0:
            return (
                "No unfinished work remains. "
                "Keep the current plan without changing its daily limit."
            )

        return (
            "No missed or overdue work was identified for the supplied "
            f"resume date of {resume_date.isoformat()}. "
            "The recommendation is to keep the current plan."
        )

    if proposal["action"] == "cannot_fit":
        return (
            "No server-validated replacement fits the unfinished work "
            f"from {resume_date.isoformat()} using the permitted daily "
            f"limits of {current_daily_minutes} to "
            f"{maximum_daily_minutes} minutes."
        )

    selected_minutes = proposal["daily_study_minutes"]
    selected_finish = finish_dates[selected_minutes]
    current_finish = finish_dates.get(current_daily_minutes)

    if selected_minutes == current_daily_minutes:
        return (
            "The unfinished work can be rescheduled at the current "
            f"{current_daily_minutes} minutes per day, finishing on "
            f"{selected_finish.isoformat()} before its exam deadlines. "
            "No daily-limit increase is needed."
        )

    if current_finish is None:
        return (
            "The current daily limit has no feasible replacement "
            "for the supplied resume date and scheduling constraints. "
            f"The selected {selected_minutes} minutes per day finishes "
            f"on {selected_finish.isoformat()} before its exam deadlines. "
            "A higher daily limit is required for this replacement."
        )

    days_saved = (current_finish - selected_finish).days

    explanation = (
        f"The current {current_daily_minutes} minutes per day is feasible, "
        f"finishing on {current_finish.isoformat()}. "
        f"The selected {selected_minutes} minutes per day finishes on "
        f"{selected_finish.isoformat()}"
    )

    if days_saved > 0:
        day_label = "day" if days_saved == 1 else "days"
        explanation += f", {days_saved} {day_label} earlier."
    elif days_saved == 0:
        explanation += ", the same finish date."
    else:
        days_later = -days_saved
        day_label = "day" if days_later == 1 else "days"
        explanation += f", {days_later} {day_label} later."

    explanation += (
        " The increase is optional, rather than required for feasibility."
    )

    if preference == "finish_sooner":
        if days_saved > 0:
            explanation += (
                " It finishes earlier than the current-limit option, "
                "consistent with your preference to finish sooner."
            )
        else:
            explanation += (
                " It provides no earlier finish than the "
                "current-limit option despite the higher daily limit."
            )
    else:
        explanation += (
            " The current-limit option also remains available "
            "with a lower daily limit."
        )

    return explanation