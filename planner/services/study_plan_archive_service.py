from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404

from planner.models import StudyPlan


def archive_study_plan(user, plan_id):
    """Archive an owned plan without deleting its sessions."""
    with transaction.atomic():
        # Use the same user lock as plan generation.
        get_user_model().objects.select_for_update().get(pk=user.pk)

        plan = get_object_or_404(
            StudyPlan.objects.select_for_update(),
            pk=plan_id,
            user=user,
        )

        if plan.status == StudyPlan.Status.ARCHIVED:
            return plan, False

        plan.status = StudyPlan.Status.ARCHIVED
        plan.save(update_fields=["status", "updated_at"])

    return plan, True