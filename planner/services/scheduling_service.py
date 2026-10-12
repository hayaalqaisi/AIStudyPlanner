from datetime import date, timedelta


REVISION_MINUTES_PER_TOPIC = 15


class SchedulingError(Exception):
    """A scheduling problem suitable for displaying to the user."""


def schedule_courses(courses, start_date, daily_study_minutes):
    """
    Schedule study and revision across courses using one daily limit.

    Each course dictionary must contain:
    - exam_id
    - exam_date
    - topics: dictionaries containing id and estimated_study_minutes

    Return session dictionaries without accessing the database.
    """
    if type(start_date) is not date:
        raise SchedulingError("The study start date must be a valid date.")

    if (
        type(daily_study_minutes) is not int
        or not 15 <= daily_study_minutes <= 720
    ):
        raise SchedulingError(
            "Daily study time must be between 15 and 720 minutes."
        )

    courses = list(courses)

    if not courses:
        raise SchedulingError("Select at least one course to schedule.")

    seen_exam_ids = set()
    seen_topic_ids = set()
    prepared_courses = []

    for course in courses:
        if not isinstance(course, dict):
            raise SchedulingError("A course has an invalid format.")

        exam_id = course.get("exam_id")
        exam_date = course.get("exam_date")
        topics = course.get("topics")

        if type(exam_id) is not int or exam_id < 1:
            raise SchedulingError("An exam has an invalid identifier.")

        if exam_id in seen_exam_ids:
            raise SchedulingError("The selected exams contain duplicates.")

        if type(exam_date) is not date or exam_date <= start_date:
            raise SchedulingError(
                "Every exam must be after the study start date."
            )

        if not isinstance(topics, list) or not topics:
            raise SchedulingError(
                "Every selected syllabus must have study topics."
            )

        prepared_topics = []

        for topic in topics:
            if not isinstance(topic, dict):
                raise SchedulingError("A topic has an invalid format.")

            topic_id = topic.get("id")
            duration = topic.get("estimated_study_minutes")

            if type(topic_id) is not int or topic_id < 1:
                raise SchedulingError("A topic has an invalid identifier.")

            if topic_id in seen_topic_ids:
                raise SchedulingError(
                    "The selected syllabi contain duplicate topics."
                )

            if type(duration) is not int or not 15 <= duration <= 1440:
                raise SchedulingError(
                    "Each topic must require between 15 and 1440 minutes."
                )

            seen_topic_ids.add(topic_id)
            prepared_topics.append(
                {
                    "id": topic_id,
                    "estimated_study_minutes": duration,
                }
            )

        seen_exam_ids.add(exam_id)
        prepared_courses.append(
            {
                "exam_id": exam_id,
                "exam_date": exam_date,
                "topics": prepared_topics,
            }
        )

    prepared_courses.sort(
        key=lambda course: (course["exam_date"], course["exam_id"])
    )

    tasks = []
    cumulative_minutes = 0

    for course in prepared_courses:
        for kind in ("study", "revision"):
            for topic in course["topics"]:
                duration = (
                    topic["estimated_study_minutes"]
                    if kind == "study"
                    else REVISION_MINUTES_PER_TOPIC
                )

                tasks.append(
                    {
                        "exam_id": course["exam_id"],
                        "exam_date": course["exam_date"],
                        "topic_id": topic["id"],
                        "kind": kind,
                        "duration_minutes": duration,
                    }
                )
                cumulative_minutes += duration

        available_days = (course["exam_date"] - start_date).days
        available_minutes = available_days * daily_study_minutes

        if cumulative_minutes > available_minutes:
            raise SchedulingError(
                f"By {course['exam_date']}, study and revision need "
                f"{cumulative_minutes} minutes, but only "
                f"{available_minutes} minutes are available. "
                "Adjust your start date, daily study time, "
                "topic estimates, or selected courses."
            )

    sessions = []
    study_date = start_date
    remaining_daily_minutes = daily_study_minutes

    for task in tasks:
        remaining_task_minutes = task["duration_minutes"]

        while remaining_task_minutes > 0:
            if remaining_daily_minutes == 0:
                study_date += timedelta(days=1)
                remaining_daily_minutes = daily_study_minutes

            if study_date >= task["exam_date"]:
                raise SchedulingError(
                    "The schedule could not finish before an exam."
                )

            session_minutes = min(
                remaining_task_minutes,
                remaining_daily_minutes,
            )

            sessions.append(
                {
                    "exam_id": task["exam_id"],
                    "topic_id": task["topic_id"],
                    "study_date": study_date,
                    "duration_minutes": session_minutes,
                    "kind": task["kind"],
                }
            )

            remaining_task_minutes -= session_minutes
            remaining_daily_minutes -= session_minutes

    return sessions