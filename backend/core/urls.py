from django.contrib import admin
from django.urls import include, path, re_path

from core.views import spa

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/trips/", include("trips.urls")),
    re_path(r"^(?P<path>.*)$", spa),
]
