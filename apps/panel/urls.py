# apps/panel/urls.py
from django.urls import path
from .views import (
    dashboard,
    requests_list,
    request_detail,
    request_action_register,
    request_action_send_for_resolution,
    request_action_create_resolution,
    request_action_add_step,
    request_action_mark_done,

    # API dashboard
    api_dashboard_all,
    api_dashboard_kpi,
    api_dashboard_requests_status,
    api_dashboard_requests_directions,
    api_dashboard_requests_regions,
    api_dashboard_requests_timeline_created,
    api_dashboard_requests_timeline_done,
    api_dashboard_sla_overdue_departments,
    api_dashboard_sla_avg_resolution,
    api_dashboard_companies_category,
    api_dashboard_companies_region,
    api_dashboard_companies_direction,
    api_dashboard_data_quality,
)

app_name = "panel"

urlpatterns = [
    # Dashboard API
    path("api/dashboard/", api_dashboard_all, name="api_dashboard_all"),
    path("api/dashboard/kpi/", api_dashboard_kpi, name="api_dashboard_kpi"),

    path("api/dashboard/requests/status/", api_dashboard_requests_status, name="api_dashboard_requests_status"),
    path("api/dashboard/requests/directions/", api_dashboard_requests_directions,
         name="api_dashboard_requests_directions"),
    path("api/dashboard/requests/regions/", api_dashboard_requests_regions, name="api_dashboard_requests_regions"),
    path("api/dashboard/requests/timeline-created/", api_dashboard_requests_timeline_created,
         name="api_dashboard_requests_timeline_created"),
    path("api/dashboard/requests/timeline-done/", api_dashboard_requests_timeline_done,
         name="api_dashboard_requests_timeline_done"),

    path("api/dashboard/sla/overdue-departments/", api_dashboard_sla_overdue_departments,
         name="api_dashboard_sla_overdue_departments"),
    path("api/dashboard/sla/avg-resolution/", api_dashboard_sla_avg_resolution,
         name="api_dashboard_sla_avg_resolution"),

    path("api/dashboard/companies/category/", api_dashboard_companies_category,
         name="api_dashboard_companies_category"),
    path("api/dashboard/companies/region/", api_dashboard_companies_region, name="api_dashboard_companies_region"),
    path("api/dashboard/companies/direction/", api_dashboard_companies_direction,
         name="api_dashboard_companies_direction"),

    path("api/dashboard/data-quality/", api_dashboard_data_quality, name="api_dashboard_data_quality"),


    path("", dashboard, name="dashboard"),

    # Requests (panel)
    path("requests/", requests_list, name="requests_list"),
    path("requests/<int:pk>/", request_detail, name="request_detail"),

    # Actions
    path("requests/<int:pk>/actions/register/", request_action_register, name="request_action_register"),
    path("requests/<int:pk>/actions/send-for-resolution/", request_action_send_for_resolution, name="request_action_send_for_resolution"),
    path("requests/<int:pk>/actions/resolution/", request_action_create_resolution, name="request_action_create_resolution"),
    path("requests/<int:pk>/actions/step/", request_action_add_step, name="request_action_add_step"),
    path("requests/<int:pk>/actions/done/", request_action_mark_done, name="request_action_mark_done"),
]
