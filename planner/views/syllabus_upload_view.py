from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from planner.forms.syllabus_upload_form import SyllabusUploadForm
from planner.services.course_service import get_course
from planner.services.syllabus_service import upload_syllabus


@login_required(login_url="accounts:login")
@require_http_methods(["GET", "POST"])
def syllabus_upload_view(request, course_id):
    course = get_course(request.user, course_id)

    if request.method == "POST":
        form = SyllabusUploadForm(
            data=request.POST,
            files=request.FILES,
        )

        if form.is_valid():
            upload_syllabus(request.user, course_id, form)
            messages.success(
                request,
                "Your syllabus was uploaded successfully.",
            )
            return redirect(
                "planner:syllabus_list",
                course_id=course.id,
            )
    else:
        form = SyllabusUploadForm()

    return render(
        request,
        "planner/syllabus_upload.html",
        {
            "course": course,
            "form": form,
        },
    )