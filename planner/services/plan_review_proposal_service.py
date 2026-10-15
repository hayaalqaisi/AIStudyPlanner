import hashlib
import json
from datetime import date

from django.contrib.auth import get_user_model
from django.core import signing
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from planner.ai.plan_review_proposal_agent import propose_plan_review
from planner.forms.study_plan_replan_form import StudyPlanReplanForm
from planner.models import AgentLog, StudyPlan, StudySession
from planner.services.plan_review_options_service import build_review_options
from planner.services.scheduling_service import SchedulingError
from planner.services.study_plan_replan_service import replan_study_plan
from planner.services.study_plan_service import get_study_plan
from planner.utils.performance import PerformanceMeasurement


PROPOSAL_SALT = "planner.plan-review-proposal.v1"
PROPOSAL_MAX_AGE_SECONDS = 600


class ReviewProposalError(Exception):
    """A proposal cannot be prepared or applied safely."""


def create_review_proposal(user, plan_id, form):
    """Ask the AI for a proposal without modifying the study plan."""
    if not form.is_valid():
        raise ValueError("The plan review form must be valid.")

    plan = get_study_plan(user, plan_id)
    resume_date = form.cleaned_data["start_date"]
    maximum = form.cleaned_data["maximum_daily_minutes"]
    preference = form.cleaned_data["preference"]

    _validate_review_date(plan, resume_date)

    if maximum < plan.daily_study_minutes:
        raise ReviewProposalError(
            "The plan's daily limit changed. Reload the review page."
        )

    sessions = _read_sessions(plan)
    fingerprint = _fingerprint(plan, sessions)
    progress = _summarize_progress(sessions, resume_date)

    with PerformanceMeasurement() as measurement:
        options = build_review_options(
            sessions,
            resume_date,
            plan.daily_study_minutes,
            maximum,
        )

        proposal = propose_plan_review(
            progress=progress,
            options=options,
            preference=preference,
            current_daily_minutes=plan.daily_study_minutes,
            maximum_daily_minutes=maximum,
            resume_date=resume_date,
        )

        selected_option = next(
            (
                option
                for option in options
                if option["daily_study_minutes"]
                == proposal["daily_study_minutes"]
            ),
            None,
        )

        # The network request finishes before database locks are taken.
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=user.pk)

            locked_plan = get_object_or_404(
                StudyPlan.objects.select_for_update(),
                pk=plan_id,
                user=user,
            )
            current_sessions = _read_sessions(locked_plan, lock=True)

            if (
                locked_plan.status != StudyPlan.Status.ACTIVE
                or _fingerprint(locked_plan, current_sessions) != fingerprint
            ):
                raise ReviewProposalError(
                    "The plan changed during the review. "
                    "Reload it and request a new proposal."
                )

            metrics = measurement.finish()

            log = AgentLog.objects.create(
                user=user,
                plan=locked_plan,
                action=AgentLog.Action.REVIEW_PLAN,
                outcome=AgentLog.Outcome.SUCCEEDED,
                decision_reason=proposal["reason"],
                result_message=(
                    f"Proposed action: {proposal['action']}. "
                    "No plan changes were applied."
                ),
                duration_ms=metrics["duration_ms"],
                memory_before_bytes=metrics["memory_before_bytes"],
                memory_after_bytes=metrics["memory_after_bytes"],
            )

            token = None

            if proposal["action"] == "replan_unfinished_work":
                token = signing.dumps(
                    {
                        "user_id": user.pk,
                        "plan_id": locked_plan.pk,
                        "fingerprint": fingerprint,
                        "resume_date": resume_date.isoformat(),
                        "daily_study_minutes": (
                            proposal["daily_study_minutes"]
                        ),
                        "maximum_daily_minutes": maximum,
                        "reason": proposal["reason"],
                        "review_log_id": log.pk,
                    },
                    salt=PROPOSAL_SALT,
                    compress=True,
                )

    return {
        **proposal,
        "option": selected_option,
        "token": token,
        "resume_date": resume_date,
        "current_daily_minutes": plan.daily_study_minutes,
        "maximum_daily_minutes": maximum,
    }


def apply_review_proposal(user, plan_id, token):
    """Apply a signed proposal after explicit student confirmation."""
    if not isinstance(token, str) or not token:
        raise ReviewProposalError(
            "The proposal is missing. Request a new review."
        )

    try:
        payload = signing.loads(
            token,
            salt=PROPOSAL_SALT,
            max_age=PROPOSAL_MAX_AGE_SECONDS,
        )
    except signing.SignatureExpired:
        raise ReviewProposalError(
            "This proposal expired. Request a new review."
        ) from None
    except signing.BadSignature:
        raise ReviewProposalError(
            "This proposal is invalid. Request a new review."
        ) from None

    if (
        not isinstance(payload, dict)
        or payload.get("user_id") != user.pk
        or payload.get("plan_id") != plan_id
    ):
        raise ReviewProposalError(
            "This proposal does not belong to this account and plan."
        )

    try:
        resume_date = date.fromisoformat(payload["resume_date"])
        daily_minutes = payload["daily_study_minutes"]
        maximum = payload["maximum_daily_minutes"]
        reason = payload["reason"]
        fingerprint = payload["fingerprint"]
        review_log_id = payload["review_log_id"]
    except (KeyError, TypeError, ValueError):
        raise ReviewProposalError(
            "The proposal data is invalid. Request a new review."
        ) from None

    if (
        type(daily_minutes) is not int
        or type(maximum) is not int
        or not 15 <= daily_minutes <= maximum <= 720
        or not isinstance(reason, str)
        or not 1 <= len(reason.strip()) <= 1000
    ):
        raise ReviewProposalError(
            "The proposed daily limit or explanation is invalid."
        )

    with PerformanceMeasurement() as measurement:
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=user.pk)

            plan = get_object_or_404(
                StudyPlan.objects.select_for_update(),
                pk=plan_id,
                user=user,
            )
            sessions = _read_sessions(plan, lock=True)

            _validate_review_date(plan, resume_date)

            if _fingerprint(plan, sessions) != fingerprint:
                raise ReviewProposalError(
                    "The plan changed after this proposal was prepared. "
                    "Request a new review."
                )

            if not AgentLog.objects.filter(
                pk=review_log_id,
                user=user,
                plan=plan,
                action=AgentLog.Action.REVIEW_PLAN,
                outcome=AgentLog.Outcome.SUCCEEDED,
            ).exists():
                raise ReviewProposalError(
                    "The proposal's review record is unavailable."
                )

            form = StudyPlanReplanForm(
                data={"start_date": resume_date.isoformat()},
                plan=plan,
            )

            if not form.is_valid():
                raise ReviewProposalError(
                    "The resume date is no longer valid. "
                    "Request a new review."
                )

            # Recalculate feasibility inside the transaction.
            replacement = replan_study_plan(
                user,
                plan.pk,
                form,
                daily_study_minutes=daily_minutes,
            )

            metrics = measurement.finish()

            AgentLog.objects.create(
                user=user,
                plan=plan,
                replacement_plan=replacement,
                action=AgentLog.Action.REPLAN,
                outcome=AgentLog.Outcome.SUCCEEDED,
                decision_reason=reason,
                result_message=(
                    "The student approved the proposal. "
                    f"Unfinished work was rescheduled with a "
                    f"{daily_minutes}-minute daily limit. "
                    "Completed work was preserved and the original "
                    "plan was archived."
                ),
                duration_ms=metrics["duration_ms"],
                memory_before_bytes=metrics["memory_before_bytes"],
                memory_after_bytes=metrics["memory_after_bytes"],
            )

    return replacement


def _validate_review_date(plan, resume_date):
    if plan.status != StudyPlan.Status.ACTIVE:
        raise ReviewProposalError(
            "Only an active study plan can be reviewed or changed."
        )

    earliest_date = max(
        timezone.localdate(),
        plan.start_date,
        plan.resume_date or plan.start_date,
    )

    if resume_date < earliest_date:
        raise ReviewProposalError(
            "The resume date is no longer valid. "
            "Choose a date on or after today and the plan's latest start."
        )


def _read_sessions(plan, lock=False):
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


def _fingerprint(plan, sessions):
    snapshot = {
        "plan_id": plan.pk,
        "status": plan.status,
        "start_date": plan.start_date,
        "resume_date": plan.resume_date,
        "daily_study_minutes": plan.daily_study_minutes,
        "sessions": sessions,
    }

    encoded = json.dumps(
        snapshot,
        cls=DjangoJSONEncoder,
        sort_keys=True,
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


def _summarize_progress(sessions, resume_date):
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