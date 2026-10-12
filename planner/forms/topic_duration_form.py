from django import forms

from planner.models import Topic


class TopicDurationForm(forms.ModelForm):
    class Meta:
        model = Topic
        fields = ("estimated_study_minutes",)
        labels = {
            "estimated_study_minutes": "Estimated study time (minutes)",
        }
        help_texts = {
            "estimated_study_minutes": (
                "Enter the total time needed for this topic, "
                "between 15 and 1440 minutes. "
                "The planner can split this work across several days."
            ),
        }
        widgets = {
            "estimated_study_minutes": forms.NumberInput(
                attrs={
                    "min": 15,
                    "max": 1440,
                    "step": 1,
                }
            ),
        }