from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from planner.forms.study_plan_replan_form import StudyPlanReplanForm
from planner.models import StudyPlan
from planner.services.plan_review_service import (
    AgentReviewServiceError,
    review_study_plan,
)
from planner.services.study_plan_service import get_study_plan


@login_required(login_url="accounts:login")
@never_cache
@require_http_methods(["GET", "POST"])
def plan_review_view(request, plan_id):
    """Review an owned active plan using the AI agent."""
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

    if request.method == "POST":
        form = StudyPlanReplanForm(
            request.POST,
            plan=plan,
        )

        if form.is_valid():
            try:
                log = review_study_plan(
                    request.user,
                    plan_id,
                    form,
                )
            except AgentReviewServiceError as error:
                form.add_error(None, str(error))
            else:
                messages.success(request, log.result_message)

                return redirect(
                    "planner:study_plan_detail",
                    plan_id=log.replacement_plan_id or plan.pk,
                )
    else:
        form = StudyPlanReplanForm(plan=plan)

    return render(
        request,
        "planner/plan_review_form.html",
        {
            "plan": plan,
            "form": form,
        },
    )