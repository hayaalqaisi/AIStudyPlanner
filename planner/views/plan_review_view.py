import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from planner.ai.plan_review_proposal_agent import ProposalGenerationError
from planner.forms.plan_review_form import PlanReviewForm
from planner.models import AgentLog, StudyPlan
from planner.services.plan_review_proposal_service import (
    ReviewProposalError,
    apply_review_proposal,
    create_review_proposal,
)
from planner.services.scheduling_service import SchedulingError
from planner.services.study_plan_service import get_study_plan
from planner.utils.performance import PerformanceMeasurement


logger = logging.getLogger(__name__)


@login_required(login_url="accounts:login")
@never_cache
@require_http_methods(["GET", "POST"])
def plan_review_view(request, plan_id):
    """Prepare a proposal or apply one explicitly approved by its owner."""
    plan = get_study_plan(request.user, plan_id)

    if plan.status != StudyPlan.Status.ACTIVE:
        messages.error(
            request,
            "Only an active study plan can be reviewed.",
        )
        return redirect(
            "planner:study_plan_detail",
            plan_id=plan.pk,
        )

    action = request.POST.get("action") if request.method == "POST" else None
    form = PlanReviewForm(
        request.POST if action == "propose" else None,
        plan=plan,
    )

    proposal = None
    review_error = ""
    response_status = 200

    if request.method == "POST":
        if action not in ("propose", "apply"):
            review_error = "Choose a valid review action."
            response_status = 400
        elif action == "apply" or form.is_valid():
            measurement = PerformanceMeasurement()

            try:
                with measurement:
                    if action == "apply":
                        replacement = apply_review_proposal(
                            request.user,
                            plan_id,
                            request.POST.get("proposal_token", ""),
                        )
                    else:
                        proposal = create_review_proposal(
                            request.user,
                            plan_id,
                            form,
                        )

            except (
                ProposalGenerationError,
                ReviewProposalError,
                SchedulingError,
            ) as error:
                review_error = str(error)
            except ValidationError:
                review_error = (
                    "The proposed changes could not be validated. "
                    "No plan changes were saved."
                )
            except DatabaseError:
                logger.error(
                    "Plan review database operation failed for plan_id=%s",
                    plan_id,
                )
                review_error = (
                    "The review could not be saved. "
                    "Please reload the page and try again."
                )
            else:
                if action == "apply":
                    messages.success(
                        request,
                        "Your approved proposal was applied. "
                        "Completed work was preserved and the original "
                        "plan was archived.",
                    )
                    return redirect(
                        "planner:study_plan_detail",
                        plan_id=replacement.pk,
                    )

            if review_error:
                _record_failure(
                    request.user,
                    plan,
                    action,
                    review_error,
                    measurement.as_dict(),
                )

    return render(
        request,
        "planner/plan_review_form.html",
        {
            "plan": plan,
            "form": form,
            "proposal": proposal,
            "review_error": review_error,
        },
        status=response_status,
    )


def _record_failure(user, plan, action, message, metrics):
    """Record a failed review without exposing technical error details."""
    try:
        AgentLog.objects.create(
            user=user,
            plan=plan,
            action=(
                AgentLog.Action.REPLAN
                if action == "apply"
                else AgentLog.Action.REVIEW_PLAN
            ),
            outcome=AgentLog.Outcome.FAILED,
            result_message=message,
            duration_ms=metrics["duration_ms"],
            memory_before_bytes=metrics["memory_before_bytes"],
            memory_after_bytes=metrics["memory_after_bytes"],
        )
    except DatabaseError:
        logger.error(
            "Saving a failed review log failed for plan_id=%s",
            plan.pk,
        )