from copy import deepcopy
from datetime import date

from django.test import SimpleTestCase

from planner.services.plan_review_options_service import (
    build_review_options,
)
from planner.services.scheduling_service import SchedulingError


class PlanReviewOptionsTests(SimpleTestCase):
    def setUp(self):
        self.resume_date = date(2030, 11, 2)

        self.sessions = [
            {
                "id": 1,
                "study_date": self.resume_date,
                "exam_date": date(2030, 11, 3),
                "duration_minutes": 30,
                "kind": "study",
                "status": "completed",
            },
            {
                "id": 2,
                "study_date": self.resume_date,
                "exam_date": date(2030, 11, 3),
                "duration_minutes": 60,
                "kind": "study",
                "status": "pending",
            },
        ]

    def test_only_feasible_limits_are_returned(self):
        options = build_review_options(
            self.sessions,
            self.resume_date,
            current_daily_minutes=60,
            maximum_daily_minutes=120,
        )

        self.assertEqual(
            [option["daily_study_minutes"] for option in options],
            [90, 105, 120],
        )

        for option in options:
            with self.subTest(option=option):
                self.assertEqual(
                    option["finish_date"],
                    "2030-11-02",
                )
                self.assertEqual(option["study_days"], 1)
                self.assertEqual(option["peak_daily_minutes"], 90)

    def test_exact_maximum_is_considered(self):
        options = build_review_options(
            self.sessions,
            self.resume_date,
            current_daily_minutes=60,
            maximum_daily_minutes=95,
        )

        self.assertEqual(
            [option["daily_study_minutes"] for option in options],
            [90, 95],
        )

    def test_no_feasible_option_returns_empty_list(self):
        options = build_review_options(
            self.sessions,
            self.resume_date,
            current_daily_minutes=60,
            maximum_daily_minutes=75,
        )

        self.assertEqual(options, [])

    def test_completed_only_plan_returns_empty_list(self):
        self.sessions = [self.sessions[0]]

        options = build_review_options(
            self.sessions,
            self.resume_date,
            current_daily_minutes=60,
            maximum_daily_minutes=120,
        )

        self.assertEqual(options, [])

    def test_source_sessions_are_not_modified(self):
        original_sessions = deepcopy(self.sessions)

        build_review_options(
            self.sessions,
            self.resume_date,
            current_daily_minutes=60,
            maximum_daily_minutes=120,
        )

        self.assertEqual(self.sessions, original_sessions)

    def test_invalid_limits_are_rejected(self):
        invalid_pairs = [
            (0, 120),
            (60, 721),
            (120, 60),
            (True, 120),
            (60, "120"),
        ]

        for current, maximum in invalid_pairs:
            with self.subTest(current=current, maximum=maximum):
                with self.assertRaises(SchedulingError):
                    build_review_options(
                        self.sessions,
                        self.resume_date,
                        current_daily_minutes=current,
                        maximum_daily_minutes=maximum,
                    )

    def test_empty_plan_is_rejected(self):
        with self.assertRaises(SchedulingError):
            build_review_options(
                [],
                self.resume_date,
                current_daily_minutes=60,
                maximum_daily_minutes=120,
            )