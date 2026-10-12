from planner.models import StudyPreference


def get_study_preference(user):
    """Return the user's saved preferences, or None if not configured."""
    return StudyPreference.objects.filter(user=user).first()


def save_study_preference(user, form):
    """Save validated study time for the current user."""
    if not form.is_valid():
        raise ValueError("The study preference form must be valid.")

    preference, created = StudyPreference.objects.update_or_create(
        user=user,
        defaults={
            "daily_study_minutes": form.cleaned_data[
                "daily_study_minutes"
            ],
        },
    )

    return preference