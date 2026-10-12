from django.db import transaction
from django.shortcuts import get_object_or_404

from planner.models import Syllabus
from planner.services.course_service import get_course


def list_syllabi(user, course_id):
    """Return uploads for a course owned by the current user."""
    course = get_course(user, course_id)
    return course.syllabi.all()


def get_syllabus(user, syllabus_id):
    """Return an owned syllabus, or raise a 404."""
    return get_object_or_404(
        Syllabus.objects.select_related("course"),
        pk=syllabus_id,
        course__user=user,
    )


def upload_syllabus(user, course_id, form):
    """Save a validated upload for an owned course."""
    course = get_course(user, course_id)

    if not form.is_valid():
        raise ValueError("The syllabus upload form must be valid.")

    uploaded_file = form.cleaned_data["file"]

    syllabus = Syllabus(
        course=course,
        original_filename=uploaded_file.name,
    )

    syllabus.file.save(
        uploaded_file.name,
        uploaded_file,
        save=False,
    )

    try:
        with transaction.atomic():
            syllabus.save()
    except Exception:
        syllabus.file.delete(save=False)
        raise

    return syllabus