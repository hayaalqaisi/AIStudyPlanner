from django import forms

from planner.models import Course


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ("name", "description")
        labels = {
            "name": "Course name",
            "description": "Description (optional)",
        }
        widgets = {
            "name": forms.TextInput(
                attrs={"placeholder": "For example, Database Systems"}
            ),
            "description": forms.Textarea(
                attrs={"rows": 4}
            ),
        }