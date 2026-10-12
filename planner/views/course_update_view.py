from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from planner.forms.course_form import CourseForm
from planner.services.course_service import get_course, update_course


@login_required(login_url="accounts:login")
@require_http_methods(["GET", "POST"])
def course_update_view(request, course_id):
    course = get_course(request.user, course_id)

    if request.method == "POST":
        form = CourseForm(request.POST, instance=course)

        if form.is_valid():
            update_course(request.user, course_id, form)
            messages.success(request, "Your course was updated successfully.")
            return redirect("planner:course_list")
    else:
        form = CourseForm(instance=course)

    return render(
        request,
        "planner/course_form.html",
        {
            "form": form,
            "page_title": "Edit course",
            "submit_label": "Save changes",
        },
    )