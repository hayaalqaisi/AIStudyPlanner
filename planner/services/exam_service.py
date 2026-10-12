from django.shortcuts import get_object_or_404

from planner.models import Exam
from planner.services.course_service import get_course


def list_exams(user, course_id):
    """Return exams for a course owned by the current user."""
    course = get_course(user, course_id)
    return course.exams.all()


def get_exam(user, exam_id):
    """Return an owned exam, or raise a 404."""
    return get_object_or_404(
        Exam.objects.select_related("course"),
        pk=exam_id,
        course__user=user,
    )


def create_exam(user, course_id, form):
    """Create an exam from a valid form for an owned course."""
    course = get_course(user, course_id)

    if not form.is_valid():
        raise ValueError("The exam form must be valid.")

    exam = Exam(
        course=course,
        title=form.cleaned_data["title"],
        exam_date=form.cleaned_data["exam_date"],
    )
    exam.full_clean()
    exam.save()

    return exam


def update_exam(user, exam_id, form):
    """Update an owned exam from a valid form."""
    exam = get_exam(user, exam_id)

    if not form.is_valid():
        raise ValueError("The exam form must be valid.")

    exam.title = form.cleaned_data["title"]
    exam.exam_date = form.cleaned_data["exam_date"]
    exam.full_clean()
    exam.save()

    return exam


def delete_exam(user, exam_id):
    """Delete an exam only if its course belongs to the current user."""
    exam = get_exam(user, exam_id)
    exam.delete()