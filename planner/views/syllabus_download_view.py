from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from planner.services.syllabus_service import get_syllabus


@login_required(login_url="accounts:login")
@never_cache
@require_GET
def syllabus_download_view(request, syllabus_id):
    syllabus = get_syllabus(request.user, syllabus_id)

    try:
        file_handle = syllabus.file.open("rb")
    except FileNotFoundError:
        raise Http404("The syllabus file could not be found.") from None

    return FileResponse(
        file_handle,
        as_attachment=True,
        filename=syllabus.original_filename,
        content_type="application/octet-stream",
    )