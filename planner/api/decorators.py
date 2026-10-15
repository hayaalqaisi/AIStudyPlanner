from functools import wraps

from django.http import JsonResponse
from django.views.decorators.cache import never_cache


def api_view_json(*, methods):
    """Require login and an allowed method for a JSON API view."""
    allowed_methods = tuple(
        dict.fromkeys(method.upper() for method in methods)
    )

    if not allowed_methods:
        raise ValueError("Specify at least one allowed HTTP method.")

    allowed_header = ", ".join(allowed_methods)
    method_description = " or ".join(allowed_methods)

    def decorator(view):
        @wraps(view)
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse(
                    {
                        "success": False,
                        "message": "Log in to access this API.",
                    },
                    status=401,
                )

            if request.method not in allowed_methods:
                response = JsonResponse(
                    {
                        "success": False,
                        "message": (
                            f"This endpoint accepts "
                            f"{method_description} requests only."
                        ),
                    },
                    status=405,
                )
                response["Allow"] = allowed_header
                return response

            return view(request, *args, **kwargs)

        return never_cache(wrapped_view)

    return decorator