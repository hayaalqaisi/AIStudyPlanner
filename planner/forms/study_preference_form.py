from django import forms

from planner.models import StudyPreference


class StudyPreferenceForm(forms.ModelForm):
    class Meta:
        model = StudyPreference
        fields = ("daily_study_minutes",)
        labels = {
            "daily_study_minutes": "Daily study time (minutes)",
        }
        help_texts = {
            "daily_study_minutes": (
                "Enter your total study time across all courses. "
                "For example, 120 minutes means 2 hours. "
                "Choose between 15 and 720 minutes."
            ),
        }
        widgets = {
            "daily_study_minutes": forms.NumberInput(
                attrs={
                    "min": 15,
                    "max": 720,
                    "step": 1,
                    "placeholder": "For example, 120",
                }
            ),
        }