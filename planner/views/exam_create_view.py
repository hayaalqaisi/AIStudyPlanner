import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from planner.forms.exam_form import ExamForm
from planner.services.course_service import get_course
from planner.services.exam_service import create_exam


logger = logging.getLogger(__name__)


@login_required(login_url="accounts:login")
@never_cache
@require_http_methods(["GET", "POST"])
def exam_create_view(request, course_id):
    """Create an exam for a course owned by the current user."""
    course = get_course(request.user, course_id)

    if request.method == "POST":
        form = ExamForm(request.POST)

        if form.is_valid():
            try:
                create_exam(request.user, course_id, form)
            except ValidationError:
                form.add_error(
                    None,
                    "The exam could not be validated. Check your details.",
                )
            except DatabaseError:
                logger.error(
                    "Creating an exam failed for course_id=%s",
                    course_id,
                )
                form.add_error(
                    None,
                    "The exam could not be saved. Please try again later.",
                )
            else:
                messages.success(
                    request,
                    "Your exam was added successfully.",
                )
                return redirect(
                    "planner:exam_list",
                    course_id=course.id,
                )
    else:
        form = ExamForm()

    return render(
        request,
        "planner/exam_form.html",
        {
            "course": course,
            "form": form,
            "page_title": "Add exam",
            "submit_label": "Add exam",
        },
    )