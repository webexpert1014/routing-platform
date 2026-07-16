from django.urls import path

from .views import GeocodeSuggestView, TripPlanView

urlpatterns = [
    path("geocode/", GeocodeSuggestView.as_view(), name="trip-geocode"),
    path("plan/", TripPlanView.as_view(), name="trip-plan"),
]
