import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from planner.forms.study_plan_replan_form import StudyPlanReplanForm
from planner.models import StudyPlan
from planner.services.scheduling_service import SchedulingError
from planner.services.study_plan_replan_service import replan_study_plan
from planner.services.study_plan_service import get_study_plan


logger = logging.getLogger(__name__)


@login_required(login_url="accounts:login")
@never_cache
@require_http_methods(["GET", "POST"])
def study_plan_replan_view(request, plan_id):
    """Replan unfinished sessions in an owned active plan."""
    plan = get_study_plan(request.user, plan_id)

    if plan.status != StudyPlan.Status.ACTIVE:
        messages.error(
            request,
            "Only an active study plan can be replanned.",
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
                replacement = replan_study_plan(
                    request.user,
                    plan_id,
                    form,
                )
            except SchedulingError as error:
                form.add_error(None, str(error))
            except ValidationError:
                logger.warning(
                    "Replanned schedule validation failed for plan_id=%s",
                    plan_id,
                )
                form.add_error(
                    None,
                    "The replacement plan could not be validated. "
                    "Your original plan has not been changed.",
                )
            except DatabaseError:
                logger.error(
                    "Saving a replanned schedule failed for plan_id=%s",
                    plan_id,
                )
                form.add_error(
                    None,
                    "The replacement plan could not be saved. "
                    "Your original plan has not been changed.",
                )
            else:
                messages.success(
                    request,
                    "Your unfinished work was rescheduled. "
                    "Completed sessions were preserved, and the "
                    "original plan was archived.",
                )
                return redirect(
                    "planner:study_plan_detail",
                    plan_id=replacement.pk,
                )
    else:
        form = StudyPlanReplanForm(plan=plan)

    return render(
        request,
        "planner/study_plan_replan_form.html",
        {
            "plan": plan,
            "form": form,
        },
    )