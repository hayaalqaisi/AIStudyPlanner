from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from planner.services.syllabus_service import get_syllabus
from planner.services.topic_service import list_topics


@login_required(login_url="accounts:login")
@never_cache
@require_GET
def topic_list_view(request, syllabus_id):
    """Display saved topics for a syllabus owned by the current user."""
    syllabus = get_syllabus(request.user, syllabus_id)
    topics = list_topics(request.user, syllabus_id)

    return render(
        request,
        "planner/topic_list.html",
        {
            "syllabus": syllabus,
            "topics": topics,
        },
    )