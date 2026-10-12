from django import forms
from django.utils import timezone


class StudyPlanReplanForm(forms.Form):
    start_date = forms.DateField(
        label="Resume studying from",
        input_formats=["%Y-%m-%d"],
        help_text=(
            "Unfinished study and revision work will be scheduled "
            "from this date."
        ),
        widget=forms.DateInput(
            format="%Y-%m-%d",
            attrs={"type": "date"},
        ),
    )

    def __init__(self, *args, plan, **kwargs):
        super().__init__(*args, **kwargs)

        self.earliest_start_date = max(
            timezone.localdate(),
            plan.start_date,
            plan.resume_date or plan.start_date,
        )
        self.fields["start_date"].initial = self.earliest_start_date
        self.fields["start_date"].widget.attrs["min"] = (
            self.earliest_start_date.isoformat()
        )

    def clean_start_date(self):
        start_date = self.cleaned_data["start_date"]

        if start_date < self.earliest_start_date:
            raise forms.ValidationError(
                "Choose a date on or after today, the original "
                "plan start, and its latest resume date."
            )

        return start_date