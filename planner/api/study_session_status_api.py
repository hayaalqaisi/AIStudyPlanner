import json
import logging

from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.http import Http404, JsonResponse

from planner.api.decorators import api_view_json
from planner.forms.study_session_status_form import StudySessionStatusForm
from planner.services.study_session_service import (
    SessionStatusError,
    get_study_session,
    update_session_status,
)


logger = logging.getLogger(__name__)


@api_view_json(methods=["PATCH"])
def study_session_status_api(request, session_id):
    """Update an owned active-plan session from a JSON PATCH request."""
    if request.content_type != "application/json":
        return JsonResponse(
            {
                "success": False,
                "message": "Send the request as application/json.",
            },
            status=415,
        )

    if len(request.body) > 4096:
        return JsonResponse(
            {
                "success": False,
                "message": "The request body is too large.",
            },
            status=413,
        )

    try:
        data = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse(
            {
                "success": False,
                "message": "Send a valid UTF-8 JSON object.",
            },
            status=400,
        )

    if (
        not isinstance(data, dict)
        or set(data) != {"status"}
        or not isinstance(data["status"], str)
    ):
        return JsonResponse(
            {
                "success": False,
                "message": "Provide only a status field containing text.",
            },
            status=400,
        )

    try:
        session = get_study_session(request.user, session_id)
        form = StudySessionStatusForm(data=data, instance=session)

        if not form.is_valid():
            return JsonResponse(
                {
                    "success": False,
                    "message": "Check the submitted session status.",
                    "errors": form.errors.get_json_data(),
                },
                status=400,
            )

        session = update_session_status(
            request.user,
            session_id,
            form,
        )
    except Http404:
        return JsonResponse(
            {
                "success": False,
                "message": "Study session not found.",
            },
            status=404,
        )
    except SessionStatusError as error:
        return JsonResponse(
            {
                "success": False,
                "message": str(error),
            },
            status=409,
        )
    except ValidationError:
        return JsonResponse(
            {
                "success": False,
                "message": "The session could not be validated.",
            },
            status=400,
        )
    except DatabaseError:
        logger.error(
            "Updating session status through the API failed "
            "for session_id=%s",
            session_id,
        )
        return JsonResponse(
            {
                "success": False,
                "message": "Session status could not be saved. "
                "Try again later.",
            },
            status=503,
        )

    return JsonResponse(
        {
            "success": True,
            "message": "Session status updated successfully.",
            "data": {
                "session": {
                    "id": session.pk,
                    "plan_id": session.plan_id,
                    "status": session.status,
                    "updated_at": session.updated_at.isoformat(),
                },
            },
        },
        status=200,
    )