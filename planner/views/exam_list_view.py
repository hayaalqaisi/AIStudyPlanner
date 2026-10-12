from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from planner.services.course_service import get_course
from planner.services.exam_service import list_exams


@login_required(login_url="accounts:login")
@never_cache
@require_GET
def exam_list_view(request, course_id):
    """Display exams for a course owned by the current user."""
    course = get_course(request.user, course_id)
    exams = list_exams(request.user, course_id)

    return render(
        request,
        "planner/exam_list.html",
        {
            "course": course,
            "exams": exams,
        },
    )