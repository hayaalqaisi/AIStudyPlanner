from django.shortcuts import get_object_or_404

from planner.models import Course


def list_courses(user):
    """Return only courses belonging to the current user."""
    return Course.objects.filter(user=user)


def get_course(user, course_id):
    """Return an owned course, or raise a 404."""
    return get_object_or_404(
        Course,
        pk=course_id,
        user=user,
    )


def create_course(user, form):
    """Create a course from a valid CourseForm."""
    if not form.is_valid():
        raise ValueError("The course form must be valid.")

    course = form.save(commit=False)
    course.user = user
    course.save()

    return course


def update_course(user, course_id, form):
    """Update an owned course from a valid CourseForm."""
    course = get_course(user, course_id)

    if not form.is_valid():
        raise ValueError("The course form must be valid.")

    course.name = form.cleaned_data["name"]
    course.description = form.cleaned_data["description"]
    course.save()

    return course


def delete_course(user, course_id):
    """Delete a course only if it belongs to the current user."""
    course = get_course(user, course_id)
    course.delete()