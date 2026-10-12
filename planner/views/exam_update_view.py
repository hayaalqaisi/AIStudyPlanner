import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from planner.forms.exam_form import ExamForm
from planner.services.exam_service import get_exam, update_exam


logger = logging.getLogger(__name__)


@login_required(login_url="accounts:login")
@never_cache
@require_http_methods(["GET", "POST"])
def exam_update_view(request, exam_id):
    """Edit an exam owned by the current user."""
    exam = get_exam(request.user, exam_id)
    course = exam.course

    if request.method == "POST":
        form = ExamForm(request.POST, instance=exam)

        if form.is_valid():
            try:
                update_exam(request.user, exam_id, form)
            except ValidationError:
                form.add_error(
                    None,
                    "The exam could not be validated. Check your details.",
                )
            except DatabaseError:
                logger.error(
                    "Updating an exam failed for exam_id=%s",
                    exam_id,
                )
                form.add_error(
                    None,
                    "The exam could not be saved. Please try again later.",
                )
            else:
                messages.success(
                    request,
                    "Your exam was updated successfully.",
                )
                return redirect(
                    "planner:exam_list",
                    course_id=course.id,
                )
    else:
        form = ExamForm(instance=exam)

    return render(
        request,
        "planner/exam_form.html",
        {
            "course": course,
            "form": form,
            "page_title": "Edit exam",
            "submit_label": "Save changes",
        },
    )