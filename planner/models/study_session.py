from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class StudySession(models.Model):
    class Kind(models.TextChoices):
        STUDY = "study", "Study"
        REVISION = "revision", "Revision"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        MISSED = "missed", "Missed"

    plan = models.ForeignKey(
        "planner.StudyPlan",
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    topic = models.ForeignKey(
        "planner.Topic",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="study_sessions",
    )
    exam = models.ForeignKey(
        "planner.Exam",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="study_sessions",
    )
    course_name = models.CharField(max_length=150)
    topic_title = models.CharField(max_length=200)
    exam_title = models.CharField(max_length=150)
    exam_date = models.DateField()
    study_date = models.DateField()
    duration_minutes = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(720),
        ],
    )
    kind = models.CharField(
        max_length=10,
        choices=Kind.choices,
        default=Kind.STUDY,
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["study_date", "id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(duration_minutes__gte=1)
                    & models.Q(duration_minutes__lte=720)
                ),
                name="session_minutes_between_1_and_720",
            ),
            models.CheckConstraint(
                condition=models.Q(study_date__lt=models.F("exam_date")),
                name="session_before_exam_date",
            ),
            models.CheckConstraint(
                condition=models.Q(kind__in=["study", "revision"]),
                name="study_session_kind_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=["pending", "completed", "missed"]
                ),
                name="study_session_status_valid",
            ),
        ]

    def clean(self):
        super().clean()

        if not self.plan_id:
            return

        plan = self.plan
        errors = {}

        if self.study_date and self.study_date < plan.start_date:
            errors["study_date"] = (
                "A session cannot be scheduled before the plan starts."
            )

        if (
            self.duration_minutes is not None
            and self.duration_minutes > plan.daily_study_minutes
        ):
            errors["duration_minutes"] = (
                "A session cannot exceed the plan's daily study limit."
            )

        if self.topic_id:
            if self.topic.syllabus.course.user_id != plan.user_id:
                errors["topic"] = "The topic must belong to the plan owner."

        if self.exam_id:
            if self.exam.course.user_id != plan.user_id:
                errors["exam"] = "The exam must belong to the plan owner."

        if self.topic_id and self.exam_id:
            if self.topic.syllabus.course_id != self.exam.course_id:
                errors["exam"] = (
                    "The topic and exam must belong to the same course."
                )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return (
            f"{self.topic_title}: {self.study_date} "
            f"({self.duration_minutes} minutes)"
        )