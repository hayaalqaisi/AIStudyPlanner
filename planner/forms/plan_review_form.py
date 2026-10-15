from django import forms

from planner.forms.study_plan_replan_form import StudyPlanReplanForm


class PlanReviewForm(StudyPlanReplanForm):
    maximum_daily_minutes = forms.IntegerField(
        label="Maximum daily study time you can accept (minutes)",
        min_value=15,
        max_value=720,
        help_text=(
            "The AI may propose a daily limit up to this amount. "
            "You will review the proposal before applying it."
        ),
        widget=forms.NumberInput(
            attrs={
                "min": 15,
                "max": 720,
                "step": 1,
            },
        ),
    )

    preference = forms.ChoiceField(
        label="What matters most for this review?",
        choices=[
            (
                "manageable_workload",
                "Keep the daily workload as light as possible",
            ),
            (
                "finish_sooner",
                "Finish sooner to leave more time before exams",
            ),
        ],
        initial="manageable_workload",
        widget=forms.RadioSelect,
    )

    def __init__(self, *args, plan, **kwargs):
        super().__init__(*args, plan=plan, **kwargs)

        self.current_daily_minutes = plan.daily_study_minutes

        self.fields["maximum_daily_minutes"].initial = (
            self.current_daily_minutes
        )
        self.fields["maximum_daily_minutes"].min_value = (
            self.current_daily_minutes
        )
        self.fields["maximum_daily_minutes"].widget.attrs["min"] = (
            self.current_daily_minutes
        )

    def clean_maximum_daily_minutes(self):
        maximum = self.cleaned_data["maximum_daily_minutes"]

        if maximum < self.current_daily_minutes:
            raise forms.ValidationError(
                "Enter an amount equal to or greater than "
                f"your current limit of {self.current_daily_minutes} minutes."
            )

        return maximum