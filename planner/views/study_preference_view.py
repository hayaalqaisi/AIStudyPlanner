import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import DatabaseError
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from planner.forms.study_preference_form import StudyPreferenceForm
from planner.services.study_preference_service import (
    get_study_preference,
    save_study_preference,
)


logger = logging.getLogger(__name__)


@login_required(login_url="accounts:login")
@never_cache
@require_http_methods(["GET", "POST"])
def study_preference_view(request):
    """Display and update the current user's daily study time."""
    preference = get_study_preference(request.user)

    if request.method == "POST":
        form = StudyPreferenceForm(
            request.POST,
            instance=preference,
        )

        if form.is_valid():
            try:
                save_study_preference(request.user, form)
            except DatabaseError:
                logger.error(
                    "Saving study preferences failed for user_id=%s",
                    request.user.id,
                )
                form.add_error(
                    None,
                    "Your settings could not be saved. "
                    "Please try again later.",
                )
            else:
                messages.success(
                    request,
                    "Your study settings were saved successfully.",
                )
                return redirect("planner:study_preferences")
    else:
        form = StudyPreferenceForm(instance=preference)

    return render(
        request,
        "planner/study_preferences.html",
        {
            "form": form,
            "has_saved_preferences": preference is not None,
        },
    )