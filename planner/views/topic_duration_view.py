import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from planner.forms.topic_duration_form import TopicDurationForm
from planner.services.topic_service import get_topic, update_topic_duration


logger = logging.getLogger(__name__)


@login_required(login_url="accounts:login")
@never_cache
@require_http_methods(["GET", "POST"])
def topic_duration_view(request, topic_id):
    """Edit estimated study time for a topic owned by the current user."""
    topic = get_topic(request.user, topic_id)

    if request.method == "POST":
        form = TopicDurationForm(request.POST, instance=topic)

        if form.is_valid():
            try:
                update_topic_duration(request.user, topic_id, form)
            except ValidationError:
                form.add_error(
                    None,
                    "The study time could not be validated. "
                    "Check the value and try again.",
                )
            except DatabaseError:
                logger.error(
                    "Updating topic duration failed for topic_id=%s",
                    topic_id,
                )
                form.add_error(
                    None,
                    "The study time could not be saved. "
                    "Please try again later.",
                )
            else:
                messages.success(
                    request,
                    "The topic study time was updated successfully.",
                )
                return redirect(
                    "planner:topic_list",
                    syllabus_id=topic.syllabus_id,
                )
    else:
        form = TopicDurationForm(instance=topic)

    return render(
        request,
        "planner/topic_duration_form.html",
        {
            "topic": topic,
            "form": form,
        },
    )