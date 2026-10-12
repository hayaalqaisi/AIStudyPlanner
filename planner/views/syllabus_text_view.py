from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from planner.services.syllabus_service import get_syllabus
from planner.services.syllabus_text_service import (
    SyllabusExtractionError,
    extract_syllabus_text,
)


@login_required(login_url="accounts:login")
@never_cache
@require_GET
def syllabus_text_view(request, syllabus_id):
    """Show extracted syllabus text only to its owner."""
    try:
        syllabus, text = extract_syllabus_text(
            request.user,
            syllabus_id,
        )
    except SyllabusExtractionError as error:
        syllabus = get_syllabus(request.user, syllabus_id)

        return render(
            request,
            "planner/syllabus_text.html",
            {
                "syllabus": syllabus,
                "text": "",
                "extraction_error": str(error),
            },
            status=422,
        )

    return render(
        request,
        "planner/syllabus_text.html",
        {
            "syllabus": syllabus,
            "text": text,
            "extraction_error": "",
        },
    )