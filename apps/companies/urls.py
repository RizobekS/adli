# apps/companies/urls.py
from django.urls import path
from .views import (
    districts_by_region,
    companies_page,
    companies_table_partial,
)

app_name = "companies"

urlpatterns = [
    path("districts-json/", districts_by_region, name="districts_by_region"),


    path("panel/companies/", companies_page, name="companies_page"),
    path("panel/companies/table/", companies_table_partial, name="companies_table_partial"),
]
