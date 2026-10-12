import logging

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from planner.ai.plan_review_agent import PlanReviewError, choose_plan_action
from planner.models import AgentLog, StudyPlan, StudySession
from planner.services.scheduling_service import SchedulingError
from planner.services.study_plan_replan_service import replan_study_plan
from planner.services.study_plan_service import get_study_plan
from planner.utils.performance import PerformanceMeasurement


logger = logging.getLogger(__name__)


class AgentReviewServiceError(Exception):
    """A review failure suitable for displaying to the user."""


def review_study_plan(user, plan_id, form):
    """Review owned progress, execute a tool, and record measurements."""
    plan = get_study_plan(user, plan_id)

    if not form.is_valid():
        raise ValueError("The plan review form must be valid.")

    action = AgentLog.Action.REVIEW_PLAN
    reason = ""

    with PerformanceMeasurement() as measurement:
        try:
            if plan.status != StudyPlan.Status.ACTIVE:
                raise SchedulingError(
                    "Only an active plan can be reviewed."
                )

            resume_date = form.cleaned_data["start_date"]
            earliest_date = max(
                timezone.localdate(),
                plan.start_date,
                plan.resume_date or plan.start_date,
            )

            if resume_date < earliest_date:
                raise SchedulingError(
                    "Choose a review date on or after today "
                    "and the plan's latest start or resume date."
                )

            original_settings = (
                plan.start_date,
                plan.resume_date,
                plan.daily_study_minutes,
            )
            original_sessions = _read_sessions(plan)

            if not original_sessions:
                raise SchedulingError(
                    "This plan has no sessions to review."
                )

            progress = _summarize_progress(
                original_sessions,
                resume_date,
            )
            decision = choose_plan_action(progress)
            reason = decision["reason"]

            action = (
                AgentLog.Action.REPLAN
                if decision["tool"] == "replan_unfinished_work"
                else AgentLog.Action.KEEP_PLAN
            )

            # OpenAI runs before database locks are acquired.
            with transaction.atomic():
                get_user_model().objects.select_for_update().get(
                    pk=user.pk
                )

                locked_plan = get_object_or_404(
                    StudyPlan.objects.select_for_update(),
                    pk=plan_id,
                    user=user,
                )

                current_sessions = _read_sessions(
                    locked_plan,
                    lock=True,
                )
                current_settings = (
                    locked_plan.start_date,
                    locked_plan.resume_date,
                    locked_plan.daily_study_minutes,
                )

                if (
                    locked_plan.status != StudyPlan.Status.ACTIVE
                    or current_settings != original_settings
                    or current_sessions != original_sessions
                ):
                    raise SchedulingError(
                        "The plan changed during the review. "
                        "Reload it and try again."
                    )

                replacement = None

                if action == AgentLog.Action.REPLAN:
                    replacement = replan_study_plan(
                        user,
                        locked_plan.pk,
                        form,
                    )
                    result_message = (
                        "Unfinished work was rescheduled. "
                        "Completed work was preserved and the original "
                        "plan was archived."
                    )
                else:
                    result_message = (
                        "No missed or overdue work requires replanning. "
                        "The current plan was kept."
                    )

                metrics = measurement.finish()

                log = AgentLog.objects.create(
                    user=user,
                    plan=locked_plan,
                    replacement_plan=replacement,
                    action=action,
                    outcome=AgentLog.Outcome.SUCCEEDED,
                    decision_reason=reason,
                    result_message=result_message,
                    duration_ms=metrics["duration_ms"],
                    memory_before_bytes=metrics["memory_before_bytes"],
                    memory_after_bytes=metrics["memory_after_bytes"],
                )

            return log

        except (PlanReviewError, SchedulingError) as error:
            message = str(error)
        except ValidationError:
            message = (
                "The agent's result could not be validated. "
                "No plan changes were saved."
            )
        except DatabaseError:
            message = (
                "The review could not be saved. "
                "No plan changes were saved."
            )

        metrics = measurement.finish()

        # Record the failure after the tool transaction rolls back.
        try:
            AgentLog.objects.create(
                user=user,
                plan_id=plan_id,
                action=action,
                outcome=AgentLog.Outcome.FAILED,
                decision_reason=reason,
                result_message=message,
                duration_ms=metrics["duration_ms"],
                memory_before_bytes=metrics["memory_before_bytes"],
                memory_after_bytes=metrics["memory_after_bytes"],
            )
        except DatabaseError:
            logger.error(
                "Saving a failed agent review log failed for plan_id=%s",
                plan_id,
            )

        raise AgentReviewServiceError(message)


def _read_sessions(plan, lock=False):
    """Read progress fields for review and change detection."""
    sessions = StudySession.objects.filter(plan=plan).order_by("id")

    if lock:
        sessions = sessions.select_for_update()

    return list(
        sessions.values(
            "id",
            "topic_id",
            "exam_id",
            "course_name",
            "topic_title",
            "exam_title",
            "study_date",
            "exam_date",
            "duration_minutes",
            "kind",
            "status",
            "updated_at",
        )
    )


def _summarize_progress(sessions, resume_date):
    """Send numeric progress totals without document text or credentials."""
    progress = {
        "completed_minutes": 0,
        "pending_minutes": 0,
        "missed_minutes": 0,
        "overdue_pending_minutes": 0,
    }

    for session in sessions:
        duration = session["duration_minutes"]
        status = session["status"]

        if status == StudySession.Status.COMPLETED:
            progress["completed_minutes"] += duration
        elif status == StudySession.Status.MISSED:
            progress["missed_minutes"] += duration
        elif status == StudySession.Status.PENDING:
            progress["pending_minutes"] += duration

            if session["study_date"] < resume_date:
                progress["overdue_pending_minutes"] += duration

    return progress
