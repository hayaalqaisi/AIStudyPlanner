from pathlib import Path
from uuid import uuid4

from django.db import models


def syllabus_upload_path(instance, filename):
    extension = Path(filename).suffix.lower()
    return f"syllabi/{uuid4().hex}{extension}"


class Syllabus(models.Model):
    course = models.ForeignKey(
        "planner.Course",
        on_delete=models.CASCADE,
        related_name="syllabi",
    )
    file = models.FileField(upload_to=syllabus_upload_path)
    original_filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at", "-id"]
        verbose_name_plural = "syllabi"

    def __str__(self):
        return f"{self.course.name}: {self.original_filename}"