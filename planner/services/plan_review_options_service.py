from collections import defaultdict
from datetime import date

from planner.services.replanning_service import schedule_remaining_sessions
from planner.services.scheduling_service import SchedulingError


def build_review_options(
    sessions,
    resume_date,
    current_daily_minutes,
    maximum_daily_minutes,
):
    """Return feasible replanning options without changing any records."""
    if type(resume_date) is not date:
        raise SchedulingError("Choose a valid resume date.")

    if (
        type(current_daily_minutes) is not int
        or type(maximum_daily_minutes) is not int
        or not 15 <= current_daily_minutes <= maximum_daily_minutes <= 720
    ):
        raise SchedulingError(
            "Review limits must be whole numbers between 15 and 720, "
            "and the maximum cannot be below the current limit."
        )

    sessions = list(sessions)

    if not sessions:
        raise SchedulingError("This plan has no sessions to review.")

    if any(not isinstance(session, dict) for session in sessions):
        raise SchedulingError("A session has an invalid format.")

    if any(
        session.get("status") not in ("pending", "completed", "missed")
        for session in sessions
    ):
        raise SchedulingError("A session has an invalid status.")

    has_unfinished_work = any(
        session["status"] in ("pending", "missed")
        for session in sessions
    )

    if not has_unfinished_work:
        return []

    candidate_limits = sorted(
        set(
            range(
                current_daily_minutes,
                maximum_daily_minutes + 1,
                15,
            )
        )
        | {maximum_daily_minutes}
    )

    options = []

    for daily_minutes in candidate_limits:
        try:
            scheduled = schedule_remaining_sessions(
                sessions,
                resume_date,
                daily_minutes,
            )
        except SchedulingError:
            continue

        daily_totals = defaultdict(int)

        for session in sessions:
            if (
                session["status"] == "completed"
                and session["study_date"] >= resume_date
            ):
                daily_totals[session["study_date"]] += (
                    session["duration_minutes"]
                )

        for session in scheduled:
            daily_totals[session["study_date"]] += (
                session["duration_minutes"]
            )

        options.append(
            {
                "daily_study_minutes": daily_minutes,
                "finish_date": max(daily_totals).isoformat(),
                "study_days": len(daily_totals),
                "peak_daily_minutes": max(daily_totals.values()),
            }
        )

    return options