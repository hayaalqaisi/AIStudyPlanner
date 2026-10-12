from planner.models import AgentLog


def list_agent_logs(user):
    """Return review logs belonging to the current user."""
    return (
        AgentLog.objects.filter(user=user)
        .select_related("plan", "replacement_plan")
        .order_by("-created_at", "-id")
    )