from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from planner.ai.plan_review_proposal_agent import ProposalGenerationError
from planner.models import AgentLog, StudyPlan, StudySession


class PlanReviewViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="review_page_student",
            password="Review-Page-Test-Password-2030!",
        )
        self.client.force_login(self.user)

        self.resume_date = timezone.localdate() + timedelta(days=1)

        self.plan = StudyPlan.objects.create(
            user=self.user,
            start_date=self.resume_date,
            daily_study_minutes=60,
        )

        for title, minutes, status in (
            ("Introduction", 30, StudySession.Status.COMPLETED),
            ("SQL queries", 60, StudySession.Status.PENDING),
        ):
            StudySession.objects.create(
                plan=self.plan,
                course_name="Database Systems",
                topic_title=title,
                exam_title="Final exam",
                exam_date=self.resume_date + timedelta(days=1),
                study_date=self.resume_date,
                duration_minutes=minutes,
                kind=StudySession.Kind.STUDY,
                status=status,
            )

        self.url = reverse(
            "planner:plan_review",
            args=[self.plan.pk],
        )

        agent_patch = patch(
            "planner.services.plan_review_proposal_service."
            "propose_plan_review",
            return_value={
                "action": "replan_unfinished_work",
                "daily_study_minutes": 90,
                "reason": "Ninety minutes fits the remaining workload.",
            },
        )
        self.mock_agent = agent_patch.start()
        self.addCleanup(agent_patch.stop)

    def request_proposal(self, **overrides):
        data = {
            "action": "propose",
            "start_date": self.resume_date.isoformat(),
            "maximum_daily_minutes": "120",
            "preference": "manageable_workload",
        }
        data.update(overrides)

        return self.client.post(self.url, data)

    def test_review_page_displays_form_without_ai_call(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Get AI proposal")
        self.assertContains(
            response,
            'name="maximum_daily_minutes"',
        )
        self.assertContains(response, 'name="preference"')
        self.mock_agent.assert_not_called()

    def test_proposal_page_requires_approval_before_changes(self):
        response = self.request_proposal()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Approve and apply proposal")
        self.assertContains(response, "Ninety minutes fits")
        self.assertTrue(response.context["proposal"]["token"])

        self.plan.refresh_from_db()

        self.assertEqual(self.plan.status, StudyPlan.Status.ACTIVE)
        self.assertEqual(self.plan.daily_study_minutes, 60)
        self.assertEqual(StudyPlan.objects.count(), 1)

    def test_approval_redirects_to_replacement_plan(self):
        proposal_response = self.request_proposal()
        token = proposal_response.context["proposal"]["token"]

        response = self.client.post(
            self.url,
            {
                "action": "apply",
                "proposal_token": token,
            },
        )

        replacement = StudyPlan.objects.get(
            replanned_from=self.plan,
        )

        self.assertRedirects(
            response,
            reverse(
                "planner:study_plan_detail",
                args=[replacement.pk],
            ),
        )
        self.assertEqual(replacement.daily_study_minutes, 90)
        self.mock_agent.assert_called_once()

    def test_invalid_form_does_not_call_ai(self):
        response = self.request_proposal(
            maximum_daily_minutes="30",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "maximum_daily_minutes",
            response.context["form"].errors,
        )
        self.mock_agent.assert_not_called()
        self.assertEqual(StudyPlan.objects.count(), 1)

    def test_ai_failure_is_displayed_and_logged(self):
        self.mock_agent.side_effect = ProposalGenerationError(
            "The plan review timed out. Please try again."
        )

        response = self.request_proposal()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The plan review timed out.")

        self.plan.refresh_from_db()

        self.assertEqual(self.plan.status, StudyPlan.Status.ACTIVE)
        self.assertEqual(StudyPlan.objects.count(), 1)
        self.assertTrue(
            AgentLog.objects.filter(
                user=self.user,
                plan=self.plan,
                action=AgentLog.Action.REVIEW_PLAN,
                outcome=AgentLog.Outcome.FAILED,
            ).exists()
        )

    def test_unknown_action_returns_400(self):
        response = self.client.post(
            self.url,
            {"action": "unsupported_action"},
        )

        self.assertEqual(response.status_code, 400)
        self.mock_agent.assert_not_called()
        self.assertEqual(StudyPlan.objects.count(), 1)

    def test_post_without_csrf_token_is_rejected(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)

        response = csrf_client.post(
            self.url,
            {
                "action": "propose",
                "start_date": self.resume_date.isoformat(),
                "maximum_daily_minutes": "120",
                "preference": "manageable_workload",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.mock_agent.assert_not_called()
        self.assertEqual(StudyPlan.objects.count(), 1)