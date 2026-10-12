from django.conf import settings
from django.db import models


class AgentLog(models.Model):
    class Action(models.TextChoices):
        REVIEW_PLAN = "review_plan", "Review plan"
        KEEP_PLAN = "keep_plan", "Keep plan"
        REPLAN = "replan", "Replan"

    class Outcome(models.TextChoices):
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="agent_logs",
    )
    plan = models.ForeignKey(
        "planner.StudyPlan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agent_logs",
    )
    replacement_plan = models.ForeignKey(
        "planner.StudyPlan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_agent_logs",
    )
    action = models.CharField(
        max_length=20,
        choices=Action.choices,
    )
    outcome = models.CharField(
        max_length=10,
        choices=Outcome.choices,
    )
    decision_reason = models.TextField(blank=True)
    result_message = models.TextField(blank=True)
    duration_ms = models.PositiveIntegerField(default=0)
    memory_before_bytes = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )
    memory_after_bytes = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    action__in=["review_plan", "keep_plan", "replan"]
                ),
                name="agent_log_action_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(outcome__in=["succeeded", "failed"]),
                name="agent_log_outcome_valid",
            ),
        ]

    @property
    def memory_delta_bytes(self):
        if (
            self.memory_before_bytes is None
            or self.memory_after_bytes is None
        ):
            return None

        return self.memory_after_bytes - self.memory_before_bytes

    def __str__(self):
        return f"{self.get_action_display()}: {self.get_outcome_display()}"