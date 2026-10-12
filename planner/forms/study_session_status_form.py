from django import forms

from planner.models import StudySession


class StudySessionStatusForm(forms.ModelForm):
    class Meta:
        model = StudySession
        fields = ("status",)
        labels = {
            "status": "Session status",
        }
        help_texts = {
            "status": (
                "Choose Completed when you finish the session, "
                "Missed when you skip it, or Pending to correct "
                "a previous update."
            ),
        }
        widgets = {
            "status": forms.Select(),
        }