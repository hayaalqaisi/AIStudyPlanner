import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import DatabaseError
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from planner.services.exam_service import delete_exam, get_exam


logger = logging.getLogger(__name__)


@login_required(login_url="accounts:login")
@never_cache
@require_http_methods(["GET", "POST"])
def exam_delete_view(request, exam_id):
    """Delete an owned exam after confirmation by POST."""
    exam = get_exam(request.user, exam_id)
    course_id = exam.course_id

    if request.method == "POST":
        try:
            delete_exam(request.user, exam_id)
        except DatabaseError:
            logger.error(
                "Deleting an exam failed for exam_id=%s",
                exam_id,
            )
            messages.error(
                request,
                "The exam could not be deleted. Please try again later.",
            )
        else:
            messages.success(
                request,
                "Your exam was deleted successfully.",
            )

        return redirect(
            "planner:exam_list",
            course_id=course_id,
        )

    return render(
        request,
        "planner/exam_confirm_delete.html",
        {"exam": exam},
    )