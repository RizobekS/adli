from django.urls import path
from .views import kerio_numbers_api, directory_page, directory_table, pull_sync, push_create_user

app_name = "telephony"

urlpatterns = [
    path("panel/api/telephony/numbers/", kerio_numbers_api, name="kerio_numbers_api"),
    path("panel/telephony/sync/pull/", pull_sync, name="pull_sync"),
    path("panel/telephony/push/create/<int:link_id>/", push_create_user, name="push_create_user"),

    # UI
    path("panel/telephony/directory/", directory_page, name="directory_page"),
    path("panel/telephony/directory/table/", directory_table, name="directory_table"),
]