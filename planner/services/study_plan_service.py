from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from planner.models import (
    Exam,
    StudyPlan,
    StudyPreference,
    StudySession,
    Syllabus,
    Topic,
)
from planner.services.scheduling_service import (
    SchedulingError,
    schedule_courses,
)


def list_study_plans(user):
    """Return only plans belonging to the current user."""
    return StudyPlan.objects.filter(user=user)


def get_study_plan(user, plan_id):
    """Return an owned plan, or raise a 404."""
    return get_object_or_404(
        StudyPlan,
        pk=plan_id,
        user=user,
    )


def generate_study_plan(user, form):
    """Generate and atomically save a plan from a validated form."""
    if not form.is_valid():
        raise ValueError("The study plan form must be valid.")

    start_date = form.cleaned_data["start_date"]
    exam_ids = [exam.pk for exam in form.cleaned_data["exams"]]
    syllabus_ids = [
        syllabus.pk for syllabus in form.cleaned_data["syllabi"]
    ]

    with transaction.atomic():
        # Serialize plan creation for this user.
        get_user_model().objects.select_for_update().get(pk=user.pk)

        if StudyPlan.objects.filter(
            user=user,
            status=StudyPlan.Status.ACTIVE,
        ).exists():
            raise SchedulingError(
                "You already have an active study plan. "
                "Archive it before generating another."
            )

        preference = (
            StudyPreference.objects.select_for_update()
            .filter(user=user)
            .first()
        )

        if preference is None:
            raise SchedulingError(
                "Save your daily study time in Study settings first."
            )

        if start_date < timezone.localdate():
            raise SchedulingError(
                "The study start date must be today or later."
            )

        exams = list(
            Exam.objects.select_for_update().filter(
                pk__in=exam_ids,
                course__user=user,
            )
        )
        syllabi = list(
            Syllabus.objects.select_for_update().filter(
                pk__in=syllabus_ids,
                course__user=user,
            )
        )

        if len(exams) != len(exam_ids) or len(syllabi) != len(syllabus_ids):
            raise SchedulingError(
                "A selected exam or syllabus is no longer available."
            )

        exam_course_ids = [exam.course_id for exam in exams]
        syllabus_course_ids = [
            syllabus.course_id for syllabus in syllabi
        ]

        if (
            len(exam_course_ids) != len(set(exam_course_ids))
            or len(syllabus_course_ids) != len(set(syllabus_course_ids))
            or set(exam_course_ids) != set(syllabus_course_ids)
        ):
            raise SchedulingError(
                "Select one exam and one syllabus for each course."
            )

        syllabi_by_course = {
            syllabus.course_id: syllabus for syllabus in syllabi
        }

        courses = []
        topics_by_id = {}
        exams_by_id = {exam.pk: exam for exam in exams}

        for exam in exams:
            syllabus = syllabi_by_course[exam.course_id]
            topics = list(
                Topic.objects.select_for_update()
                .filter(syllabus=syllabus)
                .order_by("position", "id")
            )

            topics_by_id.update({topic.pk: topic for topic in topics})

            courses.append(
                {
                    "exam_id": exam.pk,
                    "exam_date": exam.exam_date,
                    "topics": [
                        {
                            "id": topic.pk,
                            "estimated_study_minutes": (
                                topic.estimated_study_minutes
                            ),
                        }
                        for topic in topics
                    ],
                }
            )

        scheduled_sessions = schedule_courses(
            courses,
            start_date,
            preference.daily_study_minutes,
        )

        plan = StudyPlan(
            user=user,
            start_date=start_date,
            daily_study_minutes=preference.daily_study_minutes,
        )
        plan.full_clean()
        plan.save()

        sessions = []
        daily_totals = {}

        for scheduled in scheduled_sessions:
            topic = topics_by_id[scheduled["topic_id"]]
            exam = exams_by_id[scheduled["exam_id"]]

            session = StudySession(
                plan=plan,
                topic=topic,
                exam=exam,
                course_name=exam.course.name,
                topic_title=topic.title,
                exam_title=exam.title,
                exam_date=exam.exam_date,
                study_date=scheduled["study_date"],
                duration_minutes=scheduled["duration_minutes"],
                kind=scheduled["kind"],
            )
            session.full_clean()
            sessions.append(session)

            study_date = session.study_date
            daily_totals[study_date] = (
                daily_totals.get(study_date, 0)
                + session.duration_minutes
            )

        if any(
            total > plan.daily_study_minutes
            for total in daily_totals.values()
        ):
            raise SchedulingError(
                "The generated schedule exceeds your daily study limit."
            )

        StudySession.objects.bulk_create(sessions)

    return plan