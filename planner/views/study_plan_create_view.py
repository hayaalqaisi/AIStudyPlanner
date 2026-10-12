import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from planner.forms.study_plan_form import StudyPlanForm
from planner.services.scheduling_service import SchedulingError
from planner.services.study_plan_service import generate_study_plan


logger = logging.getLogger(__name__)


@login_required(login_url="accounts:login")
@never_cache
@require_http_methods(["GET", "POST"])
def study_plan_create_view(request):
    """Generate a study plan for the signed-in user."""
    if request.method == "POST":
        form = StudyPlanForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():
            try:
                plan = generate_study_plan(request.user, form)
            except SchedulingError as error:
                form.add_error(None, str(error))
            except ValidationError:
                logger.warning(
                    "Study plan validation failed for user_id=%s",
                    request.user.pk,
                )
                form.add_error(
                    None,
                    "The generated plan could not be validated. "
                    "Please check your selections and try again.",
                )
            except DatabaseError:
                logger.error(
                    "Saving a study plan failed for user_id=%s",
                    request.user.pk,
                )
                form.add_error(
                    None,
                    "Your study plan could not be saved. "
                    "Please try again later.",
                )
            else:
                messages.success(
                    request,
                    "Your study plan was generated successfully.",
                )
                return redirect(
                    "planner:study_plan_detail",
                    plan_id=plan.pk,
                )
    else:
        form = StudyPlanForm(user=request.user)

    return render(
        request,
        "planner/study_plan_form.html",
        {"form": form},
    )