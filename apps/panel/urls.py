# apps/panel/urls.py
from django.urls import path
from .views import (
    dashboard,
    analytics_requests,
    analytics_companies,
    requests_list,
    request_detail,
    request_action_add_step,
    request_action_mark_done,
    request_action_assign_executor,
    request_action_set_waiting,
    request_action_set_in_progress,

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
    api_dashboard_requests_problem_directions,
    api_analytics_requests_all,
    api_analytics_companies_all,

)

app_name = "panel"

urlpatterns = [
    # Dashboard API
    path("api/dashboard/", api_dashboard_all, name="api_dashboard_all"),
    path("api/analytics/requests/", api_analytics_requests_all, name="api_analytics_requests_all"),
    path("api/analytics/companies/", api_analytics_companies_all, name="api_analytics_companies_all"),
    path("api/dashboard/kpi/", api_dashboard_kpi, name="api_dashboard_kpi"),

    path("api/dashboard/requests/status/", api_dashboard_requests_status, name="api_dashboard_requests_status"),
    path("api/dashboard/requests/directions/", api_dashboard_requests_directions,
         name="api_dashboard_requests_directions"),
    path("api/dashboard/requests/problem-directions/", api_dashboard_requests_problem_directions,
         name="api_dashboard_requests_problem_directions"),
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
    path("analytics/requests/", analytics_requests, name="analytics_requests"),
    path("analytics/companies/", analytics_companies, name="analytics_companies"),

    # Requests (panel)
    path("requests/", requests_list, name="requests_list"),
    path("requests/<int:pk>/", request_detail, name="request_detail"),

    # Actions
    path("requests/<int:pk>/actions/assign-executor/", request_action_assign_executor, name="request_action_assign_executor"),
    path("requests/<int:pk>/actions/set-waiting/", request_action_set_waiting, name="request_action_set_waiting"),
    path("requests/<int:pk>/actions/set-in-progress/", request_action_set_in_progress, name="request_action_set_in_progress"),
    path("requests/<int:pk>/actions/step/", request_action_add_step, name="request_action_add_step"),
    path("requests/<int:pk>/actions/done/", request_action_mark_done, name="request_action_mark_done"),
]
