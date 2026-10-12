from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from planner.models import StudyPlan, StudySession
from planner.services.replanning_service import schedule_remaining_sessions
from planner.services.scheduling_service import SchedulingError


def replan_study_plan(user, plan_id, form):
    """Replace an owned active plan while preserving completed work."""
    if not form.is_valid():
        raise ValueError("The replanning form must be valid.")

    resume_date = form.cleaned_data["start_date"]

    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=user.pk)

        original_plan = get_object_or_404(
            StudyPlan.objects.select_for_update(),
            pk=plan_id,
            user=user,
        )

        if original_plan.status != StudyPlan.Status.ACTIVE:
            raise SchedulingError(
                "Only an active study plan can be replanned."
            )

        earliest_resume_date = max(
            timezone.localdate(),
            original_plan.start_date,
            original_plan.resume_date or original_plan.start_date,
        )

        if resume_date < earliest_resume_date:
            raise SchedulingError(
                "The resume date cannot be before today, "
                "the plan start, or its previous resume date."
            )

        original_sessions = list(
            StudySession.objects.select_for_update()
            .filter(plan=original_plan)
            .order_by("study_date", "id")
        )

        scheduled = schedule_remaining_sessions(
            [
                {
                    "id": session.pk,
                    "study_date": session.study_date,
                    "exam_date": session.exam_date,
                    "duration_minutes": session.duration_minutes,
                    "kind": session.kind,
                    "status": session.status,
                }
                for session in original_sessions
            ],
            resume_date,
            original_plan.daily_study_minutes,
        )

        sources = {
            session.pk: session for session in original_sessions
        }

        original_plan.status = StudyPlan.Status.ARCHIVED
        original_plan.save(update_fields=["status", "updated_at"])

        replacement = StudyPlan(
            user=user,
            replanned_from=original_plan,
            start_date=original_plan.start_date,
            resume_date=resume_date,
            daily_study_minutes=original_plan.daily_study_minutes,
        )
        replacement.full_clean()
        replacement.save()

        new_sessions = []

        for source in original_sessions:
            if source.status == StudySession.Status.COMPLETED:
                new_sessions.append(
                    _copy_session(
                        source,
                        replacement,
                        source.study_date,
                        source.duration_minutes,
                        StudySession.Status.COMPLETED,
                    )
                )

        for scheduled_session in scheduled:
            source = sources[scheduled_session["source_session_id"]]

            new_sessions.append(
                _copy_session(
                    source,
                    replacement,
                    scheduled_session["study_date"],
                    scheduled_session["duration_minutes"],
                    StudySession.Status.PENDING,
                )
            )

        daily_totals = {}

        for session in new_sessions:
            session.full_clean()
            daily_totals[session.study_date] = (
                daily_totals.get(session.study_date, 0)
                + session.duration_minutes
            )

        if any(
            total > replacement.daily_study_minutes
            for total in daily_totals.values()
        ):
            raise SchedulingError(
                "The replacement plan exceeds the daily study limit."
            )

        original_minutes = sum(
            session.duration_minutes for session in original_sessions
        )
        replacement_minutes = sum(
            session.duration_minutes for session in new_sessions
        )

        if replacement_minutes != original_minutes:
            raise SchedulingError(
                "Replanning did not preserve the total study workload."
            )

        StudySession.objects.bulk_create(new_sessions)

    return replacement


def _copy_session(source, plan, study_date, duration_minutes, status):
    """Copy saved session snapshots without changing source records."""
    return StudySession(
        plan=plan,
        topic_id=source.topic_id,
        exam_id=source.exam_id,
        course_name=source.course_name,
        topic_title=source.topic_title,
        exam_title=source.exam_title,
        exam_date=source.exam_date,
        study_date=study_date,
        duration_minutes=duration_minutes,
        kind=source.kind,
        status=status,
    )