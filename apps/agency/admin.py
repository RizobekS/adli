# apps/agency/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from modeltranslation.admin import TranslationAdmin

from .models import Department, Employee, PositionAgency


@admin.register(Department)
class DepartmentAdmin(TranslationAdmin, admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "code")
    ordering = ("name",)
    date_hierarchy = "created_at"


@admin.register(PositionAgency)
class PositionAdmin(TranslationAdmin, admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)
    ordering = ("name",)
    list_filter = ("created_at",)
    readonly_fields = ("created_at",)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("display_name", "department", "position", "pinpp", "phone", "is_active", "created_at")
    list_select_related = ("user", "department")
    list_filter = ("is_active", "department", "created_at")
    search_fields = (
        "first_name", "last_name", "middle_name", "pinpp",
        "user__username", "user__email" "position__name", "phone"
    )
    ordering = ("department__name", "user__username")
    autocomplete_fields = ("user", "department")
    date_hierarchy = "created_at"

    fieldsets = (
        (_("Пользователь"), {"fields": ("user", "first_name", "last_name", "middle_name", "pinpp", "is_active", "department", "position", "phone", "email", "mobile_phone", "photo" )}),
        (_("Служебное"), {"fields": ("created_at",)}),
    )
    readonly_fields = ("created_at",)
