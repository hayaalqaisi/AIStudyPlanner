from collections import defaultdict
from datetime import date

from django.test import SimpleTestCase

from planner.services.scheduling_service import (
    SchedulingError,
    schedule_courses,
)


class SchedulingTests(SimpleTestCase):
    def setUp(self):
        self.start_date = date(2030, 11, 1)
        self.courses = [
            {
                "exam_id": 1,
                "exam_date": date(2030, 11, 5),
                "topics": [
                    {"id": 1, "estimated_study_minutes": 90},
                    {"id": 2, "estimated_study_minutes": 60},
                ],
            },
            {
                "exam_id": 2,
                "exam_date": date(2030, 11, 7),
                "topics": [
                    {"id": 3, "estimated_study_minutes": 120},
                ],
            },
        ]

    def test_daily_limit_is_shared_across_courses(self):
        sessions = schedule_courses(
            self.courses,
            self.start_date,
            daily_study_minutes=120,
        )

        daily_totals = defaultdict(int)

        for session in sessions:
            daily_totals[session["study_date"]] += (
                session["duration_minutes"]
            )

        self.assertTrue(sessions)
        self.assertEqual(
            {session["exam_id"] for session in sessions},
            {1, 2},
        )

        for study_date, minutes in daily_totals.items():
            with self.subTest(study_date=study_date):
                self.assertLessEqual(minutes, 120)

    def test_sessions_start_on_or_after_start_and_before_exam(self):
        sessions = schedule_courses(
            self.courses,
            self.start_date,
            daily_study_minutes=120,
        )

        deadlines = {
            course["exam_id"]: course["exam_date"]
            for course in self.courses
        }

        self.assertTrue(sessions)

        for session in sessions:
            with self.subTest(session=session):
                self.assertGreaterEqual(
                    session["study_date"],
                    self.start_date,
                )
                self.assertLess(
                    session["study_date"],
                    deadlines[session["exam_id"]],
                )

    def test_study_workload_and_revision_are_preserved(self):
        sessions = schedule_courses(
            self.courses,
            self.start_date,
            daily_study_minutes=120,
        )

        topic_totals = defaultdict(int)

        for session in sessions:
            key = (session["topic_id"], session["kind"])
            topic_totals[key] += session["duration_minutes"]

        self.assertEqual(
            dict(topic_totals),
            {
                (1, "study"): 90,
                (1, "revision"): 15,
                (2, "study"): 60,
                (2, "revision"): 15,
                (3, "study"): 120,
                (3, "revision"): 15,
            },
        )

    def test_earlier_exam_is_prioritized(self):
        sessions = schedule_courses(
            list(reversed(self.courses)),
            self.start_date,
            daily_study_minutes=120,
        )

        exam_order = [session["exam_id"] for session in sessions]

        self.assertTrue(exam_order)
        self.assertEqual(exam_order, sorted(exam_order))

    def test_work_that_cannot_fit_raises_error(self):
        courses = [
            {
                "exam_id": 1,
                "exam_date": date(2030, 11, 2),
                "topics": [
                    {"id": 1, "estimated_study_minutes": 120},
                ],
            },
        ]

        # One available day holds 120 minutes, but study plus
        # revision requires 135 minutes.
        with self.assertRaises(SchedulingError):
            schedule_courses(
                courses,
                self.start_date,
                daily_study_minutes=120,
            )