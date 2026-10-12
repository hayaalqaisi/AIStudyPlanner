from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class StudyPlan(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="study_plans",
    )
    replanned_from = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replacement_plans",
    )
    start_date = models.DateField()
    resume_date = models.DateField(null=True, blank=True)
    daily_study_minutes = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(15),
            MaxValueValidator(720),
        ],
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(daily_study_minutes__gte=15)
                    & models.Q(daily_study_minutes__lte=720)
                ),
                name="plan_daily_minutes_between_15_and_720",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=["active", "archived"]),
                name="study_plan_status_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(resume_date__isnull=True)
                    | models.Q(resume_date__gte=models.F("start_date"))
                ),
                name="plan_resume_on_or_after_start",
            ),
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(status="active"),
                name="one_active_study_plan_per_user",
            ),
        ]

    def clean(self):
        super().clean()

        if self.replanned_from_id:
            if self.pk and self.replanned_from_id == self.pk:
                raise ValidationError(
                    {"replanned_from": "A plan cannot replace itself."}
                )

            if self.replanned_from.user_id != self.user_id:
                raise ValidationError(
                    {
                        "replanned_from": (
                            "The original plan must belong to the same user."
                        )
                    }
                )

    def __str__(self):
        return f"Study plan {self.pk} for user {self.user_id}"