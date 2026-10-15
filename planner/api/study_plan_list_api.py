import logging

from django.db import DatabaseError
from django.http import JsonResponse

from planner.api.decorators import api_view_json
from planner.services.study_plan_service import list_study_plans


logger = logging.getLogger(__name__)


@api_view_json(methods=["GET"])
def study_plan_list_api(request):
    """Return the authenticated user's study plans as JSON."""
    try:
        plans = [
            {
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
                "created_at": plan.created_at.isoformat(),
                "updated_at": plan.updated_at.isoformat(),
            }
            for plan in list_study_plans(request.user)
        ]
    except DatabaseError:
        logger.error(
            "Listing study plans through the API failed for user_id=%s",
            request.user.pk,
        )
        return JsonResponse(
            {
                "success": False,
                "message": "Study plans could not be loaded. Try again later.",
            },
            status=503,
        )

    return JsonResponse(
        {
            "success": True,
            "message": "Study plans loaded successfully.",
            "data": {
                "count": len(plans),
                "plans": plans,
            },
        },
        status=200,
    )