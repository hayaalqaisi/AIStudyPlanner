from django.db import transaction
from django.shortcuts import get_object_or_404

from planner.ai.topic_extractor import extract_topics
from planner.models import Syllabus, Topic
from planner.services.syllabus_service import get_syllabus
from planner.services.syllabus_text_service import extract_syllabus_text


def list_topics(user, syllabus_id):
    """Return topics only for a syllabus owned by the current user."""
    syllabus = get_syllabus(user, syllabus_id)
    return syllabus.topics.all()


def get_topic(user, topic_id):
    """Return an owned topic, or raise a 404."""
    return get_object_or_404(
        Topic.objects.select_related("syllabus__course"),
        pk=topic_id,
        syllabus__course__user=user,
    )


def update_topic_duration(user, topic_id, form):
    """Update the estimated study time of an owned topic."""
    topic = get_topic(user, topic_id)

    if not form.is_valid():
        raise ValueError("The topic duration form must be valid.")

    topic.estimated_study_minutes = form.cleaned_data[
        "estimated_study_minutes"
    ]
    topic.full_clean()
    topic.save(
        update_fields=["estimated_study_minutes", "updated_at"],
    )

    return topic


def generate_topics(user, syllabus_id):
    """Extract and save topics once for an owned syllabus."""
    syllabus = get_syllabus(user, syllabus_id)

    existing_topics = list(syllabus.topics.all())

    if existing_topics:
        return syllabus, existing_topics, False

    syllabus, text = extract_syllabus_text(user, syllabus_id)
    extracted_topics = extract_topics(text)

    # Run the network request before acquiring a database lock.
    with transaction.atomic():
        locked_syllabus = get_object_or_404(
            Syllabus.objects.select_for_update(),
            pk=syllabus.id,
            course__user=user,
        )

        # A concurrent request may already have saved the topics.
        existing_topics = list(locked_syllabus.topics.all())

        if existing_topics:
            return locked_syllabus, existing_topics, False

        topics = [
            Topic(
                syllabus=locked_syllabus,
                title=topic["title"],
                description=topic["description"],
                position=position,
            )
            for position, topic in enumerate(extracted_topics, start=1)
        ]

        for topic in topics:
            topic.full_clean()

        Topic.objects.bulk_create(topics)

    return syllabus, topics, True