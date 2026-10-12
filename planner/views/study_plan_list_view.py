from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from planner.services.study_plan_service import list_study_plans


@login_required(login_url="accounts:login")
@never_cache
@require_GET
def study_plan_list_view(request):
    """Display study plans belonging to the current user."""
    plans = list_study_plans(request.user)

    return render(
        request,
        "planner/study_plan_list.html",
        {"plans": plans},
    )