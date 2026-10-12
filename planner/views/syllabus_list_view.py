from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_GET

from planner.services.course_service import get_course
from planner.services.syllabus_service import list_syllabi


@login_required(login_url="accounts:login")
@require_GET
def syllabus_list_view(request, course_id):
    course = get_course(request.user, course_id)
    syllabi = list_syllabi(request.user, course_id)

    return render(
        request,
        "planner/syllabus_list.html",
        {
            "course": course,
            "syllabi": syllabi,
        },
    )