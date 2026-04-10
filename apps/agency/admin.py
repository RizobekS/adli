# apps/agency/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from import_export.admin import ImportExportModelAdmin
from modeltranslation.admin import TranslationAdmin

from .forms import AgencyAboutAdminForm, NewsAdminForm
from .models import Department, Employee, PositionAgency, AgencyAbout, News, LeadershipProfile, ProblemDirection
from .resources import ProblemDirectionResource


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
        "user__username", "user__email", "position__name", "phone"
    )
    ordering = ("department__name", "user__username")
    autocomplete_fields = ("user", "department")
    date_hierarchy = "created_at"

    fieldsets = (
        (_("Пользователь"), {"fields": ("user", "first_name", "last_name", "middle_name", "pinpp", "is_active", "department", "position", "phone", "email", "mobile_phone", "photo" )}),
        (_("Служебное"), {"fields": ("created_at",)}),
    )
    readonly_fields = ("created_at",)


@admin.register(ProblemDirection)
class ProblemDirectionAdmin(TranslationAdmin, ImportExportModelAdmin, admin.ModelAdmin):
    resource_class = ProblemDirectionResource

    list_display = ("name", "department", "is_active", "sort_order", "created_at")
    list_filter = ("is_active", "department", "created_at")
    search_fields = ("name", "department__name")
    ordering = ("sort_order", "name")
    autocomplete_fields = ("department",)
    readonly_fields = ("created_at",)
    list_editable = ("sort_order",)


@admin.register(AgencyAbout)
class AgencyAboutAdmin(TranslationAdmin, admin.ModelAdmin):
    list_display = ("title", "is_published", "views_count", "updated_at")
    list_filter = ("is_published", "updated_at")
    search_fields = ("title",)
    readonly_fields = ("views_count", "created_at", "updated_at")
    ordering = ("-updated_at",)

    fieldsets = (
        (_("Контент"), {"fields": ("title", "short_description", "description", "photo", "is_published")}),
        (_("Статистика"), {"fields": ("views_count",)}),
        (_("Служебное"), {"fields": ("created_at", "updated_at")}),
    )

    form = AgencyAboutAdminForm


@admin.register(LeadershipProfile)
class LeadershipProfileAdmin(TranslationAdmin, admin.ModelAdmin):
    list_display = ("employee", "is_published", "sort_order", "public_email", "views_count", "updated_at")
    list_filter = ("is_published", "updated_at")
    search_fields = (
        "employee__first_name", "employee__last_name", "employee__middle_name",
        "employee__user__username", "public_email",
    )
    ordering = ("sort_order", "employee__last_name")
    autocomplete_fields = ("employee",)
    readonly_fields = ("views_count", "created_at", "updated_at")

    fieldsets = (
        (_("Сотрудник"), {"fields": ("employee",)}),
        (_("Публикация"), {"fields": ("is_published", "sort_order")}),
        (_("Контакты"), {"fields": ("public_email", "public_site_url", "reception_time")}),
        (_("Биография"), {"fields": ("biography",)}),
        (_("Статистика"), {"fields": ("views_count",)}),
        (_("Служебное"), {"fields": ("created_at", "updated_at")}),
    )


@admin.register(News)
class NewsAdmin(TranslationAdmin, admin.ModelAdmin):
    list_display = ("title", "is_published", "announcement", "published_at", "views_count")
    list_filter = ("is_published", "announcement", "published_at")
    search_fields = ("title", "description")
    readonly_fields = ("views_count", "created_at", "updated_at")
    date_hierarchy = "published_at"
    ordering = ("-published_at",)

    fieldsets = (
        (_("Новость"), {"fields": ("title", "description", "photo", "announcement")}),
        (_("Публикация"), {"fields": ("is_published", "published_at")}),
        (_("Статистика"), {"fields": ("views_count",)}),
        (_("Служебное"), {"fields": ("created_at", "updated_at")}),
    )

    form = NewsAdminForm

