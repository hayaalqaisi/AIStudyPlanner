from datetime import date, timedelta

from planner.services.scheduling_service import SchedulingError


def schedule_remaining_sessions(
    sessions,
    start_date,
    daily_study_minutes,
):
    """
    Reschedule unfinished work without accessing the database.

    Each session dictionary must contain:
    - id
    - study_date
    - exam_date
    - duration_minutes
    - kind
    - status

    Return dictionaries referencing the original session IDs.
    """
    if type(start_date) is not date:
        raise SchedulingError("Choose a valid resume date.")

    if (
        type(daily_study_minutes) is not int
        or not 15 <= daily_study_minutes <= 720
    ):
        raise SchedulingError(
            "Daily study time must be between 15 and 720 minutes."
        )

    completed_daily_minutes = {}
    unfinished = []
    seen_ids = set()

    for session in sessions:
        if not isinstance(session, dict):
            raise SchedulingError("A session has an invalid format.")

        session_id = session.get("id")
        duration = session.get("duration_minutes")
        study_date = session.get("study_date")
        exam_date = session.get("exam_date")
        status = session.get("status")
        kind = session.get("kind")

        if type(session_id) is not int or session_id < 1:
            raise SchedulingError("A session has an invalid identifier.")

        if session_id in seen_ids:
            raise SchedulingError("The session list contains duplicates.")

        if type(duration) is not int or not 1 <= duration <= 720:
            raise SchedulingError("A session has an invalid duration.")

        if type(study_date) is not date or type(exam_date) is not date:
            raise SchedulingError("A session has an invalid date.")

        if study_date >= exam_date:
            raise SchedulingError(
                "A source session is not scheduled before its exam."
            )

        if status not in ("pending", "completed", "missed"):
            raise SchedulingError("A session has an invalid status.")

        if kind not in ("study", "revision"):
            raise SchedulingError("A session has an invalid activity.")

        seen_ids.add(session_id)

        if status == "completed":
            completed_daily_minutes[study_date] = (
                completed_daily_minutes.get(study_date, 0) + duration
            )
        else:
            if exam_date <= start_date:
                raise SchedulingError(
                    "Unfinished work has an exam on or before the "
                    "resume date. Choose an earlier date if possible."
                )

            unfinished.append(session.copy())

    if not unfinished:
        raise SchedulingError("There is no unfinished work to replan.")

    if any(
        minutes > daily_study_minutes
        for study_date, minutes in completed_daily_minutes.items()
        if study_date >= start_date
    ):
        raise SchedulingError(
            "Completed work already exceeds the daily limit "
            "on a date within the replanning period."
        )

    unfinished.sort(
        key=lambda session: (
            session["exam_date"],
            0 if session["kind"] == "study" else 1,
            session["id"],
        )
    )

    daily_totals = completed_daily_minutes.copy()
    scheduled = []
    current_date = start_date

    for session in unfinished:
        remaining_minutes = session["duration_minutes"]

        while remaining_minutes > 0:
            if current_date >= session["exam_date"]:
                raise SchedulingError(
                    "The remaining work cannot fit before its exam. "
                    "Choose an earlier resume date if possible."
                )

            available_minutes = (
                daily_study_minutes - daily_totals.get(current_date, 0)
            )

            if available_minutes <= 0:
                current_date += timedelta(days=1)
                continue

            duration = min(remaining_minutes, available_minutes)

            scheduled.append(
                {
                    "source_session_id": session["id"],
                    "study_date": current_date,
                    "duration_minutes": duration,
                }
            )

            daily_totals[current_date] = (
                daily_totals.get(current_date, 0) + duration
            )
            remaining_minutes -= duration

    return scheduled