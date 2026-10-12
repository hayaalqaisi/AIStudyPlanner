from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404

from planner.models import StudyPlan, StudySession


class SessionStatusError(Exception):
    """A session-status problem suitable for displaying to the user."""


def get_study_session(user, session_id):
    """Return a session owned by the current user, or raise a 404."""
    return get_object_or_404(
        StudySession.objects.select_related("plan"),
        pk=session_id,
        plan__user=user,
    )


def update_session_status(user, session_id, form):
    """Update an owned session while its plan is active."""
    if not form.is_valid():
        raise ValueError("The session status form must be valid.")

    with transaction.atomic():
        # Coordinate status updates with plan creation and archiving.
        get_user_model().objects.select_for_update().get(pk=user.pk)

        session = get_object_or_404(
            StudySession.objects.select_related("plan").select_for_update(),
            pk=session_id,
            plan__user=user,
        )

        if session.plan.status != StudyPlan.Status.ACTIVE:
            raise SessionStatusError(
                "Archived plans are read-only. "
                "You cannot change their session statuses."
            )

        session.status = form.cleaned_data["status"]
        session.full_clean()
        session.save(update_fields=["status", "updated_at"])

    return session