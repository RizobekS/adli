# apps/requests/admin.py
from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _

from .models import (
    Request,
    RequestFile,
    RequestResolution,
    RequestStep,
    RequestHistory,
)
from .services import (
    register_request,
    send_for_resolution,
    create_resolution,
    mark_done,
    add_step,
)


# ---------- Inlines ----------

class RequestFileInline(admin.TabularInline):
    model = RequestFile
    extra = 0
    readonly_fields = ("created_at",)
    fields = ("kind", "file", "created_at")


class RequestResolutionInline(admin.StackedInline):
    model = RequestResolution
    extra = 0
    readonly_fields = ("created_at", "author")
    fields = ("author", "text", "target_department", "target_employee", "due_date", "created_at")

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class RequestStepInline(admin.StackedInline):
    model = RequestStep
    extra = 0
    readonly_fields = ("created_at", "author")
    fields = ("author", "text", "created_at")

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class RequestHistoryInline(admin.TabularInline):
    model = RequestHistory
    extra = 0
    can_delete = False
    readonly_fields = ("created_at", "actor", "action", "from_status", "to_status", "comment")
    fields = ("created_at", "actor", "action", "from_status", "to_status", "comment")
    ordering = ("-created_at",)

    def has_add_permission(self, request, obj=None):
        return False


# ---------- Admins ----------


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "company",
        "employee",
        "public_id",
        "status",
        "assigned_department",
        "assigned_employee",
        "due_date",
        "created_at",
    )
    list_select_related = ("company", "employee", "assigned_department", "assigned_employee")
    list_filter = ("status", "directions", "assigned_department", "assigned_employee", "due_date", "created_at", "directions")
    search_fields = (
        "description",
        "public_id",
        "company__name",
        "company__inn",
        "employee__first_name",
        "employee__last_name",
        "assigned_employee__user__username",
        "assigned_employee__user__first_name",
        "assigned_employee__user__last_name",
        "assigned_department__name",
        "directions__title",
    )
    ordering = ("-created_at",)
    date_hierarchy = "created_at"

    autocomplete_fields = ("company", "directions", "assigned_department", "assigned_employee")
    readonly_fields = ("created_at", "updated_at", "resolved_at", "public_id")

    inlines = (RequestFileInline, RequestResolutionInline, RequestStepInline, RequestHistoryInline)

    fieldsets = (
        (_("Основное"), {"fields": ("company", "employee", "status", "directions", "description")}),
        (_("Назначение и контроль"), {"fields": ("assigned_department", "assigned_employee", "due_date", "resolved_at")}),
        (_("Служебное"), {"fields": ("created_at", "updated_at")}),
    )

    actions = ("action_register", "action_send_for_resolution", "action_mark_done")

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        # Блокируем ручное назначение: только через резолюцию/сервисы
        ro += ["assigned_department", "assigned_employee", "due_date"]
        return ro

    # --- Admin actions (через сервисы) ---

    @admin.action(description=_("Зарегистрировать (канцелярия)"))
    def action_register(self, request, queryset):
        cnt = 0
        for obj in queryset:
            register_request(request=obj, actor=request.user, comment=_("Действие из админки"))
            cnt += 1
        self.message_user(request, _("Зарегистрировано: %(cnt)s") % {"cnt": cnt}, level=messages.SUCCESS)

    @admin.action(description=_("Отправить на резолюцию"))
    def action_send_for_resolution(self, request, queryset):
        cnt = 0
        for obj in queryset:
            send_for_resolution(request=obj, actor=request.user, comment=_("Действие из админки"))
            cnt += 1
        self.message_user(request, _("Отправлено на резолюцию: %(cnt)s") % {"cnt": cnt}, level=messages.SUCCESS)

    @admin.action(description=_("Пометить как обработано"))
    def action_mark_done(self, request, queryset):
        cnt = 0
        for obj in queryset:
            mark_done(request=obj, actor=request.user, comment=_("Действие из админки"))
            cnt += 1
        self.message_user(request, _("Обработано: %(cnt)s") % {"cnt": cnt}, level=messages.SUCCESS)

    def save_formset(self, request, form, formset, change):
        """
        Когда пользователь добавляет RequestResolution в inline,
        мы НЕ доверяем обычному formset.save().
        Мы создаём резолюцию через сервис, чтобы синхронизировать Request + историю.
        """
        if formset.model is RequestResolution:
            instances = formset.save(commit=False)
            for inst in instances:
                text = inst.text
                dept = inst.target_department
                emp = inst.target_employee
                due = inst.due_date

                create_resolution(
                    request=form.instance,
                    author=request.user,
                    text=text,
                    target_department=dept,
                    target_employee=emp,
                    due_date=due,
                    comment=_("Резолюция добавлена из админки"),
                )
            formset.save_m2m()
            return

        if formset.model is RequestStep:
            instances = formset.save(commit=False)
            for inst in instances:
                add_step(
                    request=form.instance,
                    author=request.user,
                    text=inst.text,
                    comment=_("Шаг добавлен из админки"),
                )
            formset.save_m2m()
            return

        super().save_formset(request, form, formset, change)
