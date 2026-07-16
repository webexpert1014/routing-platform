from pathlib import Path

from django.conf import settings
from django.http import Http404, HttpResponse
from django.views.static import serve


def spa(request, path=""):
    root = Path(settings.FRONTEND_DIR)
    if path:
        candidate = root / path
        if candidate.is_file():
            return serve(request, path, document_root=root)
        if Path(path).suffix:
            raise Http404()
    index = root / "index.html"
    if not index.is_file():
        return HttpResponse(
            "Front-end build missing. From front-end/: pnpm build",
            content_type="text/plain",
            status=503,
        )
    return HttpResponse(index.read_bytes(), content_type="text/html")
