import json
from datetime import date

from planner.ai.openai_client import AIServiceError, call_openai
from planner.ai.plan_review_proposal_tools import (
    PLAN_REVIEW_PROPOSAL_TOOLS,
)
from planner.ai.plan_review_proposal_validation import (
    ProposalValidationError,
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
    """Generate a validated proposal without accessing the database."""
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

    context = {
        "progress": progress,
        "feasible_options": options,
        "preference": preference,
        "current_daily_minutes": current_daily_minutes,
        "maximum_daily_minutes": maximum_daily_minutes,
        "resume_date": resume_date.isoformat(),
    }

    try:
        instructions = load_prompt("plan_review.md")

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

    try:
        return validate_review_proposal(
            proposal,
            options=options,
            has_unfinished_work=(
                progress["pending_minutes"] + progress["missed_minutes"] > 0
            ),
            has_overdue_or_missed_work=(
                progress["overdue_pending_minutes"] > 0
                or progress["missed_minutes"] > 0
            ),
        )
    except ProposalValidationError as error:
        raise ProposalGenerationError(str(error)) from None