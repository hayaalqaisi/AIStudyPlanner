from django import forms
from django.utils import timezone

from planner.models import Exam


class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ("title", "exam_date")
        labels = {
            "title": "Exam title",
            "exam_date": "Exam date",
        }
        widgets = {
            "title": forms.TextInput(
                attrs={"placeholder": "For example, Final exam"}
            ),
            "exam_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"},
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.original_exam_date = (
            self.instance.exam_date
            if self.instance.pk
            else None
        )

        self.fields["exam_date"].input_formats = ["%Y-%m-%d"]

    def clean_title(self):
        title = self.cleaned_data["title"].strip()

        if not title:
            raise forms.ValidationError("Enter an exam title.")

        return title

    def clean_exam_date(self):
        exam_date = self.cleaned_data["exam_date"]

        if (
            exam_date < timezone.localdate()
            and exam_date != self.original_exam_date
        ):
            raise forms.ValidationError(
                "Choose today or a future date."
            )

        return exam_date