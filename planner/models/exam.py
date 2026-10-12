from django.db import models


class Exam(models.Model):
    course = models.ForeignKey(
        "planner.Course",
        on_delete=models.CASCADE,
        related_name="exams",
    )
    title = models.CharField(max_length=150)
    exam_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["exam_date", "id"]

    def __str__(self):
        return f"{self.course.name}: {self.title} ({self.exam_date})"