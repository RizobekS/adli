# apps/companies/urls.py
from django.urls import path
from .views import (
    districts_by_region,
    companies_page,
    companies_table_partial, directions_by_category_json,
)

app_name = "companies"

urlpatterns = [
    path("districts-json/", districts_by_region, name="districts_by_region"),
    path("directions-json/", directions_by_category_json, name="directions_by_category_json"),


    path("panel/companies/", companies_page, name="companies_page"),
    path("panel/companies/table/", companies_table_partial, name="companies_table_partial"),
]
