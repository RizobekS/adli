from django.urls import path
from .views import (
    public_request_create,
    public_request_success,
    public_track_requests,
    public_request_history_json,
    htmx_directions_by_category,
)

app_name = "requests"

urlpatterns = [
    path("request/", public_request_create, name="public_request_create"),

    path("request/success/<str:token>/", public_request_success, name="public_request_success"),

    path("track/", public_track_requests, name="public_track_requests"),
    path("track/history/<str:public_id>/", public_request_history_json, name="public_request_history_json"),
    path("htmx/directions/", htmx_directions_by_category, name="htmx_directions_by_category"),
]
