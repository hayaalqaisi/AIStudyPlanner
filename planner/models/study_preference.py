from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class StudyPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="study_preference",
    )
    daily_study_minutes = models.PositiveSmallIntegerField(
        default=120,
        validators=[
            MinValueValidator(15),
            MaxValueValidator(720),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(daily_study_minutes__gte=15)
                    & models.Q(daily_study_minutes__lte=720)
                ),
                name="daily_study_minutes_between_15_and_720",
            ),
        ]

    def __str__(self):
        return (
            f"Study preferences for user {self.user_id}: "
            f"{self.daily_study_minutes} minutes per day"
        )