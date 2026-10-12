import logging

from django.db import DatabaseError
from django.http import Http404, JsonResponse
from django.views.decorators.cache import never_cache

from planner.services.study_plan_service import get_study_plan


logger = logging.getLogger(__name__)


@never_cache
def study_plan_detail_api(request, plan_id):
    """Return an owned study plan and its sessions as JSON."""
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
        plan = get_study_plan(request.user, plan_id)

        sessions = [
            {
                "id": session.pk,
                "topic_id": session.topic_id,
                "exam_id": session.exam_id,
                "course_name": session.course_name,
                "topic_title": session.topic_title,
                "exam_title": session.exam_title,
                "exam_date": session.exam_date.isoformat(),
                "study_date": session.study_date.isoformat(),
                "duration_minutes": session.duration_minutes,
                "kind": session.kind,
                "status": session.status,
            }
            for session in plan.sessions.all().order_by("study_date", "id")
        ]

        plan_data = {
            "id": plan.pk,
            "status": plan.status,
            "start_date": plan.start_date.isoformat(),
            "resume_date": (
                plan.resume_date.isoformat()
                if plan.resume_date
                else None
            ),
            "daily_study_minutes": plan.daily_study_minutes,
            "replanned_from_id": plan.replanned_from_id,
            "total_minutes": sum(
                session["duration_minutes"] for session in sessions
            ),
            "session_count": len(sessions),
            "sessions": sessions,
        }
    except Http404:
        return JsonResponse(
            {
                "success": False,
                "message": "Study plan not found.",
            },
            status=404,
        )
    except DatabaseError:
        logger.error(
            "Loading a study plan through the API failed for plan_id=%s",
            plan_id,
        )
        return JsonResponse(
            {
                "success": False,
                "message": "Study plan could not be loaded. Try again later.",
            },
            status=503,
        )

    return JsonResponse(
        {
            "success": True,
            "message": "Study plan loaded successfully.",
            "data": {
                "plan": plan_data,
            },
        },
        status=200,
    )