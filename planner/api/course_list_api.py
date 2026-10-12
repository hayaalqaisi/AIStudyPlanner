import logging

from django.db import DatabaseError
from django.http import JsonResponse
from django.views.decorators.cache import never_cache

from planner.services.course_service import list_courses


logger = logging.getLogger(__name__)


@never_cache
def course_list_api(request):
    """Return the authenticated user's courses as JSON."""
    if not request.user.is_authenticated:
        return JsonResponse(
            {
                "success": False,
                "message": "Log in to access this API.",
            },
            status=401,
        )

    if request.method != "GET":
        response = JsonResponse(
            {
                "success": False,
                "message": "This endpoint accepts GET requests only.",
            },
            status=405,
        )
        response["Allow"] = "GET"
        return response

    try:
        courses = [
            {
                "id": course.pk,
                "name": course.name,
                "description": course.description,
                "created_at": course.created_at.isoformat(),
                "updated_at": course.updated_at.isoformat(),
            }
            for course in list_courses(request.user)
        ]
    except DatabaseError:
        logger.error(
            "Listing courses through the API failed for user_id=%s",
            request.user.pk,
        )
        return JsonResponse(
            {
                "success": False,
                "message": "Courses could not be loaded. Try again later.",
            },
            status=503,
        )

    return JsonResponse(
        {
            "success": True,
            "message": "Courses loaded successfully.",
            "data": {
                "count": len(courses),
                "courses": courses,
            },
        },
        status=200,
    )