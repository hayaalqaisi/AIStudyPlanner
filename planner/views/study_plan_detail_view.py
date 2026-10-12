from itertools import groupby

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from planner.services.study_plan_service import get_study_plan


@login_required(login_url="accounts:login")
@never_cache
@require_GET
def study_plan_detail_view(request, plan_id):
    """Display a study plan belonging to the current user."""
    plan = get_study_plan(request.user, plan_id)

    sessions = list(
        plan.sessions.all().order_by("study_date", "id")
    )

    days = []

    for study_date, grouped_sessions in groupby(
        sessions,
        key=lambda session: session.study_date,
    ):
        day_sessions = list(grouped_sessions)

        days.append(
            {
                "date": study_date,
                "sessions": day_sessions,
                "total_minutes": sum(
                    session.duration_minutes
                    for session in day_sessions
                ),
            }
        )

    return render(
        request,
        "planner/study_plan_detail.html",
        {
            "plan": plan,
            "days": days,
            "total_minutes": sum(
                session.duration_minutes for session in sessions
            ),
        },
    )