from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from planner.services.agent_log_service import list_agent_logs


@login_required(login_url="accounts:login")
@never_cache
@require_GET
def agent_log_list_view(request):
    """Display paginated agent-review history for the current user."""
    logs = list_agent_logs(request.user)
    paginator = Paginator(logs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "planner/agent_log_list.html",
        {"page_obj": page_obj},
    )