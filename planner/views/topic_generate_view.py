import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from planner.ai.topic_extractor import TopicExtractionError
from planner.services.syllabus_service import get_syllabus
from planner.services.syllabus_text_service import SyllabusExtractionError
from planner.services.topic_service import generate_topics


logger = logging.getLogger(__name__)


@login_required(login_url="accounts:login")
@require_POST
def topic_generate_view(request, syllabus_id):
    """Generate topics only for a syllabus owned by the current user."""
    # Check ownership before processing or handling extraction errors.
    get_syllabus(request.user, syllabus_id)

    try:
        syllabus, topics, created = generate_topics(
            request.user,
            syllabus_id,
        )
    except (SyllabusExtractionError, TopicExtractionError) as error:
        messages.error(request, str(error))
    except ValidationError:
        logger.warning(
            "Topic validation failed for syllabus_id=%s",
            syllabus_id,
        )
        messages.error(
            request,
            "The extracted topics could not be validated. Please try again.",
        )
    except DatabaseError:
        logger.error(
            "Saving topics failed for syllabus_id=%s",
            syllabus_id,
        )
        messages.error(
            request,
            "Topics could not be saved. Please try again later.",
        )
    else:
        if created:
            messages.success(
                request,
                f"{len(topics)} study topics were extracted and saved.",
            )
        else:
            messages.info(
                request,
                "This syllabus already has saved topics.",
            )

    return redirect(
        "planner:topic_list",
        syllabus_id=syllabus_id,
    )