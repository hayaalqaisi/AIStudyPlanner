from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Topic(models.Model):
    syllabus = models.ForeignKey(
        "planner.Syllabus",
        on_delete=models.CASCADE,
        related_name="topics",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    position = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )
    estimated_study_minutes = models.PositiveSmallIntegerField(
        default=60,
        validators=[
            MinValueValidator(15),
            MaxValueValidator(1440),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["syllabus", "position"],
                name="unique_topic_position_per_syllabus",
            ),
            models.CheckConstraint(
                condition=models.Q(position__gte=1),
                name="topic_position_at_least_one",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(estimated_study_minutes__gte=15)
                    & models.Q(estimated_study_minutes__lte=1440)
                ),
                name="topic_study_minutes_between_15_and_1440",
            ),
        ]

    def __str__(self):
        return self.title