import time
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from planner.forms.plan_review_form import PlanReviewForm
from planner.models import AgentLog, StudyPlan, StudySession
from planner.services.plan_review_proposal_service import (
    ReviewProposalError,
    apply_review_proposal,
    create_review_proposal,
)


class ReviewProposalServiceTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="proposal_student",
            password="Proposal-Test-Password-2030!",
        )
        self.other_user = User.objects.create_user(
            username="another_student",
            password="Another-Test-Password-2030!",
        )

        self.resume_date = timezone.localdate() + timedelta(days=1)
        self.plan = StudyPlan.objects.create(
            user=self.user,
            start_date=self.resume_date,
            daily_study_minutes=60,
        )

        self.completed = StudySession.objects.create(
            plan=self.plan,
            course_name="Database Systems",
            topic_title="Introduction",
            exam_title="Final exam",
            exam_date=self.resume_date + timedelta(days=1),
            study_date=self.resume_date,
            duration_minutes=30,
            kind=StudySession.Kind.STUDY,
            status=StudySession.Status.COMPLETED,
        )

        self.pending = StudySession.objects.create(
            plan=self.plan,
            course_name="Database Systems",
            topic_title="SQL queries",
            exam_title="Final exam",
            exam_date=self.resume_date + timedelta(days=1),
            study_date=self.resume_date,
            duration_minutes=60,
            kind=StudySession.Kind.STUDY,
            status=StudySession.Status.PENDING,
        )

        agent_patch = patch(
            "planner.services.plan_review_proposal_service."
            "propose_plan_review",
            return_value={
                "action": "replan_unfinished_work",
                "daily_study_minutes": 90,
                "reason": "Ninety minutes accommodates the remaining work.",
            },
        )
        self.mock_agent = agent_patch.start()
        self.addCleanup(agent_patch.stop)

    def make_proposal(self, maximum=120):
        form = PlanReviewForm(
            data={
                "start_date": self.resume_date.isoformat(),
                "maximum_daily_minutes": str(maximum),
                "preference": "manageable_workload",
            },
            plan=self.plan,
        )

        self.assertTrue(form.is_valid(), form.errors.as_json())

        return create_review_proposal(
            self.user,
            self.plan.pk,
            form,
        )

    def assert_original_unchanged(self):
        self.plan.refresh_from_db()

        self.assertEqual(self.plan.status, StudyPlan.Status.ACTIVE)
        self.assertEqual(self.plan.daily_study_minutes, 60)
        self.assertEqual(StudyPlan.objects.count(), 1)
        self.assertEqual(self.plan.sessions.count(), 2)

    def test_creating_proposal_does_not_change_plan(self):
        proposal = self.make_proposal()

        self.assert_original_unchanged()
        self.assertTrue(proposal["token"])
        self.assertEqual(proposal["daily_study_minutes"], 90)
        self.assertEqual(
            proposal["option"]["daily_study_minutes"],
            90,
        )

        log = AgentLog.objects.get()
        self.assertEqual(log.action, AgentLog.Action.REVIEW_PLAN)
        self.assertIsNone(log.replacement_plan_id)

        arguments = self.mock_agent.call_args.kwargs
        self.assertEqual(
            [
                option["daily_study_minutes"]
                for option in arguments["options"]
            ],
            [90, 105, 120],
        )

    def test_approval_applies_proposal_without_second_ai_call(self):
        proposal = self.make_proposal()

        replacement = apply_review_proposal(
            self.user,
            self.plan.pk,
            proposal["token"],
        )

        self.mock_agent.assert_called_once()
        self.plan.refresh_from_db()

        self.assertEqual(self.plan.status, StudyPlan.Status.ARCHIVED)
        self.assertEqual(replacement.status, StudyPlan.Status.ACTIVE)
        self.assertEqual(replacement.daily_study_minutes, 90)
        self.assertEqual(replacement.replanned_from_id, self.plan.pk)

        completed = replacement.sessions.get(
            status=StudySession.Status.COMPLETED,
        )
        self.assertEqual(completed.study_date, self.completed.study_date)
        self.assertEqual(completed.duration_minutes, 30)

        self.assertEqual(
            sum(
                session.duration_minutes
                for session in replacement.sessions.all()
            ),
            90,
        )

        self.assertEqual(AgentLog.objects.count(), 2)
        self.assertTrue(
            AgentLog.objects.filter(
                action=AgentLog.Action.REPLAN,
                replacement_plan=replacement,
            ).exists()
        )

    def test_tampered_token_is_rejected(self):
        proposal = self.make_proposal()

        with self.assertRaises(ReviewProposalError):
            apply_review_proposal(
                self.user,
                self.plan.pk,
                proposal["token"] + "tampered",
            )

        self.assert_original_unchanged()

    def test_another_user_cannot_apply_proposal(self):
        proposal = self.make_proposal()

        with self.assertRaises(ReviewProposalError):
            apply_review_proposal(
                self.other_user,
                self.plan.pk,
                proposal["token"],
            )

        self.assert_original_unchanged()

    def test_changed_session_invalidates_proposal(self):
        proposal = self.make_proposal()

        StudySession.objects.filter(pk=self.pending.pk).update(
            status=StudySession.Status.MISSED,
        )

        with self.assertRaises(ReviewProposalError):
            apply_review_proposal(
                self.user,
                self.plan.pk,
                proposal["token"],
            )

        self.assert_original_unchanged()
        self.pending.refresh_from_db()
        self.assertEqual(
            self.pending.status,
            StudySession.Status.MISSED,
        )

    def test_expired_proposal_is_rejected(self):
        proposal = self.make_proposal()
        future_time = time.time() + 601

        with patch(
            "django.core.signing.time.time",
            return_value=future_time,
        ):
            with self.assertRaises(ReviewProposalError):
                apply_review_proposal(
                    self.user,
                    self.plan.pk,
                    proposal["token"],
                )

        self.assert_original_unchanged()

    def test_applied_proposal_cannot_be_reused(self):
        proposal = self.make_proposal()

        apply_review_proposal(
            self.user,
            self.plan.pk,
            proposal["token"],
        )

        with self.assertRaises(ReviewProposalError):
            apply_review_proposal(
                self.user,
                self.plan.pk,
                proposal["token"],
            )

        self.assertEqual(StudyPlan.objects.count(), 2)
        self.assertEqual(
            StudyPlan.objects.filter(
                status=StudyPlan.Status.ACTIVE,
            ).count(),
            1,
        )
        self.assertEqual(
            AgentLog.objects.filter(
                action=AgentLog.Action.REPLAN,
            ).count(),
            1,
        )

    def test_cannot_fit_proposal_has_no_approval_token(self):
        self.mock_agent.return_value = {
            "action": "cannot_fit",
            "daily_study_minutes": None,
            "reason": "No feasible schedule fits within sixty minutes.",
        }

        proposal = self.make_proposal(maximum=60)

        self.assertEqual(proposal["action"], "cannot_fit")
        self.assertIsNone(proposal["token"])
        self.assertIsNone(proposal["option"])
        self.assert_original_unchanged()