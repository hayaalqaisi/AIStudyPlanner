import json
import os

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

from planner.ai.plan_review_tools import PLAN_REVIEW_TOOLS


REVIEW_INSTRUCTIONS = """
Review the supplied study-plan progress summary.

Choose exactly one tool:
- replan_unfinished_work when missed_minutes or
  overdue_pending_minutes is greater than zero.
- keep_current_plan when both are zero.

Overdue pending work means Pending sessions scheduled before the
user's selected resume date.

Completed work must never be repeated.
Do not invent progress, dates, available capacity, or exam deadlines.
The server validates scheduling feasibility before changing the plan.
Do not claim that a replacement plan has already been created.
Give a brief factual reason for your tool choice.
"""


class PlanReviewError(Exception):
    """An agent-review problem suitable for displaying to the user."""


def choose_plan_action(progress):
    """Choose an approved tool without accessing the database."""
    required_fields = {
        "completed_minutes",
        "pending_minutes",
        "missed_minutes",
        "overdue_pending_minutes",
    }

    if not isinstance(progress, dict) or set(progress) != required_fields:
        raise PlanReviewError("The progress summary has an invalid format.")

    if any(
        type(value) is not int or value < 0
        for value in progress.values()
    ):
        raise PlanReviewError(
            "Progress totals must be nonnegative whole numbers."
        )

    if progress["overdue_pending_minutes"] > progress["pending_minutes"]:
        raise PlanReviewError("The overdue work total is invalid.")

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "").strip()

    if not api_key or not model:
        raise PlanReviewError(
            "OpenAI configuration is missing. "
            "Check OPENAI_API_KEY and OPENAI_MODEL."
        )

    try:
        with OpenAI(
            api_key=api_key,
            timeout=60.0,
            max_retries=0,
        ) as client:
            response = client.responses.create(
                model=model,
                instructions=REVIEW_INSTRUCTIONS,
                input=json.dumps(progress),
                tools=PLAN_REVIEW_TOOLS,
                tool_choice="required",
                parallel_tool_calls=False,
                max_output_tokens=500,
                store=False,
            )
    except AuthenticationError:
        raise PlanReviewError(
            "OpenAI authentication failed. Check your API key."
        ) from None
    except RateLimitError:
        raise PlanReviewError(
            "OpenAI could not accept the request. "
            "Check API quota, billing, and rate limits."
        ) from None
    except APITimeoutError:
        raise PlanReviewError(
            "The plan review timed out. Please try again."
        ) from None
    except APIConnectionError:
        raise PlanReviewError(
            "Could not connect to OpenAI. Check your internet connection."
        ) from None
    except APIStatusError:
        raise PlanReviewError(
            "OpenAI could not complete the plan review."
        ) from None

    if response.status != "completed":
        raise PlanReviewError("The agent did not complete its review.")

    calls = [
        item
        for item in response.output
        if item.type == "function_call"
    ]

    if len(calls) != 1:
        raise PlanReviewError("The agent must choose exactly one tool.")

    call = calls[0]

    if call.name not in ("keep_current_plan", "replan_unfinished_work"):
        raise PlanReviewError("The agent selected an unsupported tool.")

    try:
        arguments = json.loads(call.arguments)
    except json.JSONDecodeError:
        raise PlanReviewError(
            "The agent returned unreadable tool arguments."
        ) from None

    if not isinstance(arguments, dict) or set(arguments) != {"reason"}:
        raise PlanReviewError("The tool arguments have an invalid format.")

    reason = arguments["reason"]

    if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 1000:
        raise PlanReviewError("The agent returned an invalid explanation.")

    needs_replanning = (
        progress["missed_minutes"] > 0
        or progress["overdue_pending_minutes"] > 0
    )
    expected_tool = (
        "replan_unfinished_work"
        if needs_replanning
        else "keep_current_plan"
    )

    if call.name != expected_tool:
        raise PlanReviewError(
            "The agent's decision does not match the supplied progress."
        )

    return {
        "tool": call.name,
        "reason": reason.strip(),
    }