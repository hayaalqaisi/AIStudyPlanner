from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from planner.forms.study_plan_replan_form import StudyPlanReplanForm
from planner.models import StudyPlan, StudySession
from planner.services.scheduling_service import SchedulingError
from planner.services.study_plan_replan_service import replan_study_plan


class ReplanServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="replan_student",
            password="Replan-Test-Password-2030!",
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
            topic_title="Introduction to databases",
            exam_title="Final exam",
            exam_date=self.resume_date + timedelta(days=1),
            study_date=self.resume_date,
            duration_minutes=30,
            kind=StudySession.Kind.STUDY,
            status=StudySession.Status.COMPLETED,
        )

        self.unfinished = StudySession.objects.create(
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

    def make_form(self):
        form = StudyPlanReplanForm(
            data={"start_date": self.resume_date.isoformat()},
            plan=self.plan,
        )
        self.assertTrue(form.is_valid(), form.errors.as_json())
        return form

    def assert_original_plan_unchanged(self):
        self.plan.refresh_from_db()
        self.completed.refresh_from_db()
        self.unfinished.refresh_from_db()

        self.assertEqual(self.plan.status, StudyPlan.Status.ACTIVE)
        self.assertEqual(self.plan.daily_study_minutes, 60)
        self.assertEqual(StudyPlan.objects.count(), 1)
        self.assertEqual(self.plan.sessions.count(), 2)
        self.assertEqual(
            self.completed.status,
            StudySession.Status.COMPLETED,
        )
        self.assertEqual(
            self.unfinished.status,
            StudySession.Status.PENDING,
        )

    def test_increased_limit_creates_feasible_replacement(self):
        replacement = replan_study_plan(
            self.user,
            self.plan.pk,
            self.make_form(),
            daily_study_minutes=90,
        )

        self.plan.refresh_from_db()

        self.assertEqual(self.plan.status, StudyPlan.Status.ARCHIVED)
        self.assertEqual(self.plan.daily_study_minutes, 60)
        self.assertEqual(replacement.status, StudyPlan.Status.ACTIVE)
        self.assertEqual(replacement.daily_study_minutes, 90)
        self.assertEqual(replacement.replanned_from_id, self.plan.pk)
        self.assertEqual(replacement.resume_date, self.resume_date)

        sessions = list(replacement.sessions.all())

        self.assertEqual(len(sessions), 2)
        self.assertEqual(
            sum(session.duration_minutes for session in sessions),
            90,
        )

        completed = replacement.sessions.get(
            status=StudySession.Status.COMPLETED
        )
        self.assertEqual(completed.topic_title, self.completed.topic_title)
        self.assertEqual(completed.study_date, self.completed.study_date)
        self.assertEqual(
            completed.duration_minutes,
            self.completed.duration_minutes,
        )

        pending = replacement.sessions.get(
            status=StudySession.Status.PENDING
        )
        self.assertEqual(pending.topic_title, self.unfinished.topic_title)
        self.assertEqual(pending.duration_minutes, 60)

        for session in sessions:
            self.assertLess(session.study_date, session.exam_date)

    def test_default_limit_failure_preserves_original_plan(self):
        with self.assertRaises(SchedulingError):
            replan_study_plan(
                self.user,
                self.plan.pk,
                self.make_form(),
            )

        self.assert_original_plan_unchanged()

    def test_insufficient_increase_preserves_original_plan(self):
        with self.assertRaises(SchedulingError):
            replan_study_plan(
                self.user,
                self.plan.pk,
                self.make_form(),
                daily_study_minutes=75,
            )

        self.assert_original_plan_unchanged()

    def test_invalid_limits_are_rejected(self):
        for invalid_limit in (0, 721, True, "90", 90.5):
            with self.subTest(daily_study_minutes=invalid_limit):
                with self.assertRaises(SchedulingError):
                    replan_study_plan(
                        self.user,
                        self.plan.pk,
                        self.make_form(),
                        daily_study_minutes=invalid_limit,
                    )

                self.assert_original_plan_unchanged()

    def test_reduced_limit_is_rejected(self):
        with self.assertRaises(SchedulingError):
            replan_study_plan(
                self.user,
                self.plan.pk,
                self.make_form(),
                daily_study_minutes=45,
            )

        self.assert_original_plan_unchanged()