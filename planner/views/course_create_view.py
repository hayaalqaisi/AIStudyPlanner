from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from planner.forms.course_form import CourseForm
from planner.services.course_service import create_course


@login_required(login_url="accounts:login")
@require_http_methods(["GET", "POST"])
def course_create_view(request):
    if request.method == "POST":
        form = CourseForm(request.POST)

        if form.is_valid():
            create_course(request.user, form)
            messages.success(request, "Your course was added successfully.")
            return redirect("planner:course_list")
    else:
        form = CourseForm()

    return render(
        request,
        "planner/course_form.html",
        {
            "form": form,
            "page_title": "Add course",
            "submit_label": "Add course",
        },
    )