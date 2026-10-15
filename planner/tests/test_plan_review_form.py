from datetime import timedelta
from types import SimpleNamespace

from django.test import SimpleTestCase
from django.utils import timezone

from planner.forms.plan_review_form import PlanReviewForm


class PlanReviewFormTests(SimpleTestCase):
    def setUp(self):
        self.start_date = timezone.localdate() + timedelta(days=2)
        self.plan = SimpleNamespace(
            start_date=self.start_date,
            resume_date=None,
            daily_study_minutes=120,
        )

    def make_form(self, **overrides):
        data = {
            "start_date": self.start_date.isoformat(),
            "maximum_daily_minutes": "180",
            "preference": "manageable_workload",
        }
        data.update(overrides)

        return PlanReviewForm(data=data, plan=self.plan)

    def test_valid_preferences_are_accepted(self):
        for preference in ("manageable_workload", "finish_sooner"):
            with self.subTest(preference=preference):
                form = self.make_form(preference=preference)

                self.assertTrue(
                    form.is_valid(),
                    form.errors.as_json(),
                )
                self.assertEqual(
                    form.cleaned_data["maximum_daily_minutes"],
                    180,
                )
                self.assertEqual(
                    form.cleaned_data["preference"],
                    preference,
                )

    def test_current_limit_is_accepted_as_maximum(self):
        form = self.make_form(maximum_daily_minutes="120")

        self.assertTrue(form.is_valid(), form.errors.as_json())

    def test_maximum_below_current_limit_is_rejected(self):
        form = self.make_form(maximum_daily_minutes="119")

        self.assertFalse(form.is_valid())
        self.assertIn("maximum_daily_minutes", form.errors)

    def test_maximum_above_720_is_rejected(self):
        form = self.make_form(maximum_daily_minutes="721")

        self.assertFalse(form.is_valid())
        self.assertIn("maximum_daily_minutes", form.errors)

    def test_fractional_minutes_are_rejected(self):
        form = self.make_form(maximum_daily_minutes="180.5")

        self.assertFalse(form.is_valid())
        self.assertIn("maximum_daily_minutes", form.errors)

    def test_unknown_preference_is_rejected(self):
        form = self.make_form(preference="unsupported_preference")

        self.assertFalse(form.is_valid())
        self.assertIn("preference", form.errors)

    def test_date_before_plan_start_is_rejected(self):
        form = self.make_form(
            start_date=(
                self.start_date - timedelta(days=1)
            ).isoformat(),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("start_date", form.errors)

    def test_date_before_latest_resume_date_is_rejected(self):
        self.plan.resume_date = self.start_date + timedelta(days=3)

        form = self.make_form()

        self.assertFalse(form.is_valid())
        self.assertIn("start_date", form.errors)