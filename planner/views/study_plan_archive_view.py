import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import DatabaseError
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from planner.services.study_plan_archive_service import archive_study_plan
from planner.services.study_plan_service import get_study_plan


logger = logging.getLogger(__name__)


@login_required(login_url="accounts:login")
@never_cache
@require_http_methods(["GET", "POST"])
def study_plan_archive_view(request, plan_id):
    """Archive an owned study plan after confirmation."""
    plan = get_study_plan(request.user, plan_id)

    if request.method == "POST":
        try:
            plan, archived = archive_study_plan(request.user, plan_id)
        except DatabaseError:
            logger.error(
                "Archiving a study plan failed for plan_id=%s",
                plan_id,
            )
            messages.error(
                request,
                "The plan could not be archived. Please try again later.",
            )
        else:
            if archived:
                messages.success(
                    request,
                    "Your study plan was archived. "
                    "Its sessions remain available in your history.",
                )
            else:
                messages.info(
                    request,
                    "This study plan is already archived.",
                )

        return redirect(
            "planner:study_plan_detail",
            plan_id=plan_id,
        )

    return render(
        request,
        "planner/study_plan_confirm_archive.html",
        {"plan": plan},
    )