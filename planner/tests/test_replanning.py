from collections import defaultdict
from datetime import date

from django.test import SimpleTestCase

from planner.services.replanning_service import (
    schedule_remaining_sessions,
)
from planner.services.scheduling_service import SchedulingError


class ReplanningTests(SimpleTestCase):
    def setUp(self):
        self.resume_date = date(2030, 11, 2)
        self.sessions = [
            {
                "id": 1,
                "study_date": self.resume_date,
                "exam_date": date(2030, 11, 5),
                "duration_minutes": 60,
                "kind": "study",
                "status": "completed",
            },
            {
                "id": 2,
                "study_date": date(2030, 11, 1),
                "exam_date": date(2030, 11, 5),
                "duration_minutes": 90,
                "kind": "study",
                "status": "missed",
            },
            {
                "id": 3,
                "study_date": date(2030, 11, 3),
                "exam_date": date(2030, 11, 5),
                "duration_minutes": 15,
                "kind": "revision",
                "status": "pending",
            },
        ]

    def test_completed_work_is_not_rescheduled(self):
        scheduled = schedule_remaining_sessions(
            self.sessions,
            self.resume_date,
            daily_study_minutes=120,
        )

        source_ids = {
            session["source_session_id"]
            for session in scheduled
        }

        self.assertEqual(source_ids, {2, 3})

        # The input completed session also remains unchanged.
        self.assertEqual(self.sessions[0]["status"], "completed")
        self.assertEqual(
            self.sessions[0]["study_date"],
            self.resume_date,
        )

    def test_completed_work_counts_toward_daily_capacity(self):
        scheduled = schedule_remaining_sessions(
            self.sessions,
            self.resume_date,
            daily_study_minutes=120,
        )

        daily_totals = defaultdict(int)

        for session in self.sessions:
            if session["status"] == "completed":
                daily_totals[session["study_date"]] += (
                    session["duration_minutes"]
                )

        for session in scheduled:
            daily_totals[session["study_date"]] += (
                session["duration_minutes"]
            )

        self.assertEqual(daily_totals[self.resume_date], 120)

        for study_date, minutes in daily_totals.items():
            with self.subTest(study_date=study_date):
                self.assertLessEqual(minutes, 120)

    def test_unfinished_workload_and_deadlines_are_preserved(self):
        scheduled = schedule_remaining_sessions(
            self.sessions,
            self.resume_date,
            daily_study_minutes=120,
        )

        sources = {
            session["id"]: session
            for session in self.sessions
        }
        rescheduled_minutes = defaultdict(int)

        for session in scheduled:
            source_id = session["source_session_id"]
            source = sources[source_id]

            rescheduled_minutes[source_id] += (
                session["duration_minutes"]
            )

            with self.subTest(session=session):
                self.assertGreaterEqual(
                    session["study_date"],
                    self.resume_date,
                )
                self.assertLess(
                    session["study_date"],
                    source["exam_date"],
                )

        self.assertEqual(
            dict(rescheduled_minutes),
            {2: 90, 3: 15},
        )

    def test_impossible_remaining_work_raises_error(self):
        sessions = [
            {
                "id": 1,
                "study_date": date(2030, 11, 1),
                "exam_date": date(2030, 11, 3),
                "duration_minutes": 120,
                "kind": "study",
                "status": "missed",
            },
        ]

        # Only November 2 is available: 60 minutes cannot
        # accommodate 120 minutes of unfinished work.
        with self.assertRaises(SchedulingError):
            schedule_remaining_sessions(
                sessions,
                self.resume_date,
                daily_study_minutes=60,
            )