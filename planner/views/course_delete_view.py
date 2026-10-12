from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from planner.services.course_service import delete_course, get_course


@login_required(login_url="accounts:login")
@require_http_methods(["GET", "POST"])
def course_delete_view(request, course_id):
    course = get_course(request.user, course_id)

    if request.method == "POST":
        delete_course(request.user, course_id)
        messages.success(request, "Your course was deleted successfully.")
        return redirect("planner:course_list")

    return render(
        request,
        "planner/course_confirm_delete.html",
        {"course": course},
    )