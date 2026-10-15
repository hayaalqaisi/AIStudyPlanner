"""Synthetic scenarios for evaluating AI plan-review recommendations."""

from datetime import date, timedelta


RESUME_DATE = date(2030, 11, 2)


def _session(
    session_id,
    *,
    minutes,
    status,
    study_date,
    exam_date,
):
    return {
        "id": session_id,
        "study_date": study_date,
        "exam_date": exam_date,
        "duration_minutes": minutes,
        "kind": "study",
        "status": status,
    }


PLAN_REVIEW_CASES = [
    {
        "name": "completed_plan_kept",
        "resume_date": RESUME_DATE,
        "current_daily_minutes": 60,
        "maximum_daily_minutes": 120,
        "preference": "manageable_workload",
        "expected_action": "keep_current_plan",
        "preference_check": None,
        "sessions": [
            _session(
                1,
                minutes=60,
                status="completed",
                study_date=RESUME_DATE - timedelta(days=1),
                exam_date=RESUME_DATE + timedelta(days=6),
            ),
        ],
    },
    {
        "name": "missed_work_lighter_workload",
        "resume_date": RESUME_DATE,
        "current_daily_minutes": 60,
        "maximum_daily_minutes": 120,
        "preference": "manageable_workload",
        "expected_action": "replan_unfinished_work",
        "preference_check": "lowest_feasible_limit",
        "sessions": [
            _session(
                1,
                minutes=60,
                status="missed",
                study_date=RESUME_DATE - timedelta(days=1),
                exam_date=RESUME_DATE + timedelta(days=6),
            ),
            _session(
                2,
                minutes=60,
                status="pending",
                study_date=RESUME_DATE,
                exam_date=RESUME_DATE + timedelta(days=6),
            ),
            _session(
                3,
                minutes=60,
                status="pending",
                study_date=RESUME_DATE + timedelta(days=1),
                exam_date=RESUME_DATE + timedelta(days=6),
            ),
            _session(
                4,
                minutes=60,
                status="pending",
                study_date=RESUME_DATE + timedelta(days=2),
                exam_date=RESUME_DATE + timedelta(days=6),
            ),
        ],
    },
    {
        "name": "missed_work_finish_sooner",
        "resume_date": RESUME_DATE,
        "current_daily_minutes": 60,
        "maximum_daily_minutes": 120,
        "preference": "finish_sooner",
        "expected_action": "replan_unfinished_work",
        "preference_check": "earliest_finish_lowest_limit",
        "sessions": [
            _session(
                1,
                minutes=60,
                status="missed",
                study_date=RESUME_DATE - timedelta(days=1),
                exam_date=RESUME_DATE + timedelta(days=6),
            ),
            _session(
                2,
                minutes=60,
                status="pending",
                study_date=RESUME_DATE,
                exam_date=RESUME_DATE + timedelta(days=6),
            ),
            _session(
                3,
                minutes=60,
                status="pending",
                study_date=RESUME_DATE + timedelta(days=1),
                exam_date=RESUME_DATE + timedelta(days=6),
            ),
            _session(
                4,
                minutes=60,
                status="pending",
                study_date=RESUME_DATE + timedelta(days=2),
                exam_date=RESUME_DATE + timedelta(days=6),
            ),
        ],
    },
    {
        "name": "completed_work_requires_higher_limit",
        "resume_date": RESUME_DATE,
        "current_daily_minutes": 60,
        "maximum_daily_minutes": 120,
        "preference": "manageable_workload",
        "expected_action": "replan_unfinished_work",
        "preference_check": "lowest_feasible_limit",
        "sessions": [
            _session(
                1,
                minutes=30,
                status="completed",
                study_date=RESUME_DATE,
                exam_date=RESUME_DATE + timedelta(days=1),
            ),
            _session(
                2,
                minutes=60,
                status="missed",
                study_date=RESUME_DATE - timedelta(days=1),
                exam_date=RESUME_DATE + timedelta(days=1),
            ),
        ],
    },
    {
        "name": "maximum_limit_insufficient",
        "resume_date": RESUME_DATE,
        "current_daily_minutes": 60,
        "maximum_daily_minutes": 75,
        "preference": "finish_sooner",
        "expected_action": "cannot_fit",
        "preference_check": None,
        "sessions": [
            _session(
                1,
                minutes=30,
                status="completed",
                study_date=RESUME_DATE,
                exam_date=RESUME_DATE + timedelta(days=1),
            ),
            _session(
                2,
                minutes=60,
                status="missed",
                study_date=RESUME_DATE - timedelta(days=1),
                exam_date=RESUME_DATE + timedelta(days=1),
            ),
        ],
    },
    {
        "name": "exam_deadline_reached",
        "resume_date": RESUME_DATE,
        "current_daily_minutes": 60,
        "maximum_daily_minutes": 120,
        "preference": "finish_sooner",
        "expected_action": "cannot_fit",
        "preference_check": None,
        "sessions": [
            _session(
                1,
                minutes=60,
                status="missed",
                study_date=RESUME_DATE - timedelta(days=1),
                exam_date=RESUME_DATE,
            ),
        ],
    },
]