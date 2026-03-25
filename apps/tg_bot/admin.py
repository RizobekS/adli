from django.contrib import admin

from .models import TelegramProfile, TelegramChatBinding


@admin.register(TelegramProfile)
class TelegramProfileAdmin(admin.ModelAdmin):
    list_display = (
        "telegram_user_id",
        "phone_normalized",
        "company",
        "employee_company",
        "is_verified",
        "is_active",
        "created_at",
    )
    list_filter = ("is_verified", "is_active", "created_at")
    search_fields = (
        "telegram_user_id",
        "username",
        "first_name",
        "last_name",
        "phone",
        "phone_normalized",
        "company__name",
        "employee_company__first_name",
        "employee_company__last_name",
        "employee_company__middle_name",
        "employee_company__phone",
    )
    autocomplete_fields = ("company", "employee_company")


@admin.register(TelegramChatBinding)
class TelegramChatBindingAdmin(admin.ModelAdmin):
    list_display = ("title", "chat_id", "chat_type", "department", "is_active", "created_at")
    list_filter = ("chat_type", "is_active", "created_at")
    search_fields = ("title", "chat_id")
    autocomplete_fields = ("department",)