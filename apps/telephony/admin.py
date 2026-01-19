from django.contrib import admin

from apps.telephony.models import TelephonyLink


@admin.register(TelephonyLink)
class TelephonyLinkAdmin(admin.ModelAdmin):
    list_display = ("employee", "extension", "kerio_guid")
    list_filter = ("employee",)
    search_fields = ("employee", "extension", "kerio_guid")


