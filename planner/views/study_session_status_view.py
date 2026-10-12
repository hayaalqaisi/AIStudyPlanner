import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from planner.forms.study_session_status_form import StudySessionStatusForm
from planner.models import StudyPlan
from planner.services.study_session_service import (
    SessionStatusError,
    get_study_session,
    update_session_status,
)


logger = logging.getLogger(__name__)


@login_required(login_url="accounts:login")
@never_cache
@require_http_methods(["GET", "POST"])
def study_session_status_view(request, session_id):
    """Display and update the status of an owned session."""
    session = get_study_session(request.user, session_id)

    if session.plan.status != StudyPlan.Status.ACTIVE:
        messages.error(
            request,
            "Archived plans are read-only. "
            "You cannot change their session statuses.",
        )
        return redirect(
            "planner:study_plan_detail",
            plan_id=session.plan_id,
        )

    if request.method == "POST":
        form = StudySessionStatusForm(
            request.POST,
            instance=session,
        )

        if form.is_valid():
            try:
                updated_session = update_session_status(
                    request.user,
                    session_id,
                    form,
                )
            except SessionStatusError as error:
                messages.error(request, str(error))
                return redirect(
                    "planner:study_plan_detail",
                    plan_id=session.plan_id,
                )
            except ValidationError:
                form.add_error(
                    None,
                    "The session could not be validated. "
                    "Please try again.",
                )
            except DatabaseError:
                logger.error(
                    "Updating session status failed for session_id=%s",
                    session_id,
                )
                form.add_error(
                    None,
                    "The session status could not be saved. "
                    "Please try again later.",
                )
            else:
                messages.success(
                    request,
                    "The session status was updated successfully.",
                )
                return redirect(
                    "planner:study_plan_detail",
                    plan_id=updated_session.plan_id,
                )
    else:
        form = StudySessionStatusForm(instance=session)

    return render(
        request,
        "planner/study_session_status_form.html",
        {
            "session": session,
            "form": form,
        },
    )