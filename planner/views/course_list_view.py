from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_GET

from planner.services.course_service import list_courses


@login_required(login_url="accounts:login")
@require_GET
def course_list_view(request):
    courses = list_courses(request.user)

    return render(
        request,
        "planner/course_list.html",
        {"courses": courses},
    )