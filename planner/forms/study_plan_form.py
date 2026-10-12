from django import forms
from django.utils import timezone

from planner.models import Exam, Syllabus


class StudyPlanForm(forms.Form):
    start_date = forms.DateField(
        label="Study start date",
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(
            format="%Y-%m-%d",
            attrs={"type": "date"},
        ),
    )
    exams = forms.ModelMultipleChoiceField(
        queryset=Exam.objects.none(),
        label="Exams to prepare for",
        widget=forms.CheckboxSelectMultiple,
        help_text="Select one exam per course.",
    )
    syllabi = forms.ModelMultipleChoiceField(
        queryset=Syllabus.objects.none(),
        label="Syllabi to study",
        widget=forms.CheckboxSelectMultiple,
        help_text=(
            "Select one syllabus with extracted topics "
            "for each selected course."
        ),
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)

        today = timezone.localdate()
        self.fields["start_date"].initial = today

        self.fields["exams"].queryset = (
            Exam.objects.filter(
                course__user=user,
                exam_date__gt=today,
            )
            .select_related("course")
            .order_by("exam_date", "id")
        )

        self.fields["syllabi"].queryset = (
            Syllabus.objects.filter(
                course__user=user,
                topics__isnull=False,
            )
            .select_related("course")
            .distinct()
            .order_by("course__name", "-uploaded_at", "-id")
        )

    def clean_start_date(self):
        start_date = self.cleaned_data["start_date"]

        if start_date < timezone.localdate():
            raise forms.ValidationError(
                "The study start date must be today or later."
            )

        return start_date

    def clean(self):
        cleaned_data = super().clean()

        start_date = cleaned_data.get("start_date")
        exams = cleaned_data.get("exams")
        syllabi = cleaned_data.get("syllabi")

        if exams is None or syllabi is None:
            return cleaned_data

        exam_course_ids = [exam.course_id for exam in exams]
        syllabus_course_ids = [
            syllabus.course_id for syllabus in syllabi
        ]

        if len(exam_course_ids) != len(set(exam_course_ids)):
            self.add_error(
                "exams",
                "Select only one exam per course.",
            )

        if len(syllabus_course_ids) != len(set(syllabus_course_ids)):
            self.add_error(
                "syllabi",
                "Select only one syllabus per course.",
            )

        if set(exam_course_ids) != set(syllabus_course_ids):
            self.add_error(
                None,
                "Each selected course must have exactly one exam "
                "and one syllabus.",
            )

        if start_date is not None:
            if any(exam.exam_date <= start_date for exam in exams):
                self.add_error(
                    "start_date",
                    "The study start date must be before every selected exam.",
                )

        return cleaned_data