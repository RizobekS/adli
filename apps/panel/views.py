# apps/panel/views.py
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_GET, require_POST

from apps.users.decorators import agency_required
from apps.requests.models import Request
from apps.requests.services import (
    register_request,
    send_for_resolution,
    create_resolution,
    add_step,
    mark_done, assign_executor,
    set_waiting, set_in_progress,
)
from .forms import (
    ResolutionForm,
    StepForm,
    PanelRequestFilterForm,
    AssignExecutorForm,
    OverdueReportFilterForm,
)
from .services.request_buckets import visible_requests_qs, apply_bucket
from .services.request_reports import (
    build_overdue_report_rows,
    build_overdue_report_workbook,
    summarize_overdue_rows,
)
from ..agency.models import Employee

from .services.analytics import (
    build_dashboard_payload,
    build_requests_payload,
    build_companies_payload,
    get_kpi,
    requests_by_status,
    requests_by_direction,
    requests_by_region,
    requests_timeline_created,
    requests_timeline_done,
    sla_overdue_by_department,
    sla_avg_resolution_days,
    companies_by_category,
    companies_by_region,
    companies_by_direction,
    data_quality_summary, requests_by_problem_direction,
)

# --- Roles (auth.Group names) ---
GROUP_CHANCELLERY = "chancellery"
GROUP_DEPUTY_ASSISTANT = "deputy_assistant"
GROUP_EXECUTOR = "executor"
GROUP_DIRECTORS = "directors"
GROUP_HEAD_OF_DEPARTMENT = "head_of_department"


def _is_htmx(request) -> bool:
    return request.headers.get("HX-Request") == "true"


def _in_group(user, name: str) -> bool:
    if not user or not user.is_authenticated:
        return False
    return user.groups.filter(name=name).exists()


def _can_write(user) -> bool:
    return _in_group(user, GROUP_HEAD_OF_DEPARTMENT) or _in_group(user, GROUP_EXECUTOR)


def _must_be_director(user) -> None:
    if not _in_group(user, GROUP_DIRECTORS):
        raise Http404()


def _filter_queryset_for_user(qs, user):
    """
    Видимость (что пользователь ВООБЩЕ может видеть):
    - chancellery: всё
    - directors: всё (read-only)
    - deputy_assistant: только обращения, где deputy_assistant = он
    - head_of_department: обращения своего департамента (assigned_department = dept)
    - executor: только assigned_employee = он
    """
    if _in_group(user, GROUP_CHANCELLERY) or _in_group(user, GROUP_DIRECTORS):
        return qs

    emp = getattr(user, "agency_employee", None)
    if not emp:
        return qs.none()

    if _in_group(user, GROUP_DEPUTY_ASSISTANT):
        return qs.filter(deputy_assistant=emp)

    if _in_group(user, GROUP_HEAD_OF_DEPARTMENT):
        # начальник видит всё по своему департаменту
        return qs.filter(assigned_department=emp.department)

    if _in_group(user, GROUP_EXECUTOR):
        # исполнитель видит только свои
        return qs.filter(assigned_employee=emp)

    # прочие роли (если зайдут) ничего не видят
    return qs.none()


@require_GET
@agency_required
def analytics_requests(request):
    return render(request, "panel/analytics_requests.html", {"kpi": get_kpi(user=request.user)})

@require_GET
@agency_required
def analytics_companies(request):
    return render(request, "panel/analytics_companies.html", {"kpi": get_kpi(user=request.user)})


def _overdue_report_filters(request):
    default_report_date = timezone.localdate()
    form = OverdueReportFilterForm(request.GET or None, initial={"report_date": default_report_date})

    if not request.GET:
        return form, None, default_report_date, True

    if not form.is_valid():
        return form, None, default_report_date, False

    return form, form.cleaned_data.get("department"), form.cleaned_data["report_date"], True


@require_GET
@agency_required
def overdue_requests_report(request):
    _must_be_director(request.user)
    form, department, report_date, is_valid = _overdue_report_filters(request)
    rows = build_overdue_report_rows(report_date=report_date, department=department) if is_valid else []
    summary = summarize_overdue_rows(rows)

    context = {
        "form": form,
        "report_date": report_date,
        "department": department,
        "summary": summary,
        "rows_preview": rows[:50],
        "rows_total": len(rows),
        "query_string": request.GET.urlencode(),
    }
    return render(request, "panel/reports/overdue_requests.html", context)


@require_GET
@agency_required
def overdue_requests_report_export(request):
    _must_be_director(request.user)
    form, department, report_date, is_valid = _overdue_report_filters(request)
    if not is_valid:
        messages.error(request, _("Проверьте параметры отчета."))
        return redirect("panel:overdue_requests_report")

    rows = build_overdue_report_rows(report_date=report_date, department=department)
    content = build_overdue_report_workbook(rows=rows, report_date=report_date)

    department_part = f"department-{department.pk}" if department else "all-departments"
    filename = f"overdue_requests_{department_part}_{report_date.isoformat()}.xlsx"
    response = HttpResponse(
        content,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@require_GET
@agency_required
@cache_page(30)
def api_analytics_requests_all(request):
    data = build_requests_payload(user=request.user)
    return JsonResponse(data, safe=True)

@require_GET
@agency_required
@cache_page(60)
def api_analytics_companies_all(request):
    # компании обычно меняются реже, поэтому можно 60с
    data = build_companies_payload(user=request.user)
    return JsonResponse(data, safe=True)


@require_GET
@agency_required
def dashboard(request):
    context = {
        "kpi": get_kpi(user=request.user),
    }
    return render(request, "panel/dashboard.html", context)


@require_GET
@agency_required
@cache_page(30)  # 30 секунд достаточно, чтобы не мучить БД при каждом refresh
def api_dashboard_all(request):
    """
    One-shot payload для dashboard.
    Фронт может одним запросом получить всё.
    """
    data = build_dashboard_payload(user=request.user)
    return JsonResponse(data, safe=True)


@require_GET
@agency_required
@cache_page(30)
def api_dashboard_kpi(request):
    return JsonResponse(get_kpi(user=request.user), safe=True)


@require_GET
@agency_required
@cache_page(30)
def api_dashboard_requests_status(request):
    return JsonResponse(requests_by_status(user=request.user), safe=True)


@require_GET
@agency_required
@cache_page(30)
def api_dashboard_requests_directions(request):
    limit = int(request.GET.get("limit") or 12)
    return JsonResponse(requests_by_direction(user=request.user, limit=limit), safe=True)


@require_GET
@agency_required
@cache_page(30)
def api_dashboard_requests_problem_directions(request):
    limit = int(request.GET.get("limit") or 12)
    return JsonResponse(requests_by_problem_direction(user=request.user, limit=limit), safe=True)


@require_GET
@agency_required
@cache_page(30)
def api_dashboard_requests_regions(request):
    limit = int(request.GET.get("limit") or 14)
    return JsonResponse(requests_by_region(user=request.user, limit=limit), safe=True)


@require_GET
@agency_required
@cache_page(30)
def api_dashboard_requests_timeline_created(request):
    days = int(request.GET.get("days") or 30)
    return JsonResponse(requests_timeline_created(user=request.user, days=days), safe=True)


@require_GET
@agency_required
@cache_page(30)
def api_dashboard_requests_timeline_done(request):
    days = int(request.GET.get("days") or 30)
    return JsonResponse(requests_timeline_done(user=request.user, days=days), safe=True)


@require_GET
@agency_required
@cache_page(30)
def api_dashboard_sla_overdue_departments(request):
    limit = int(request.GET.get("limit") or 10)
    return JsonResponse(sla_overdue_by_department(user=request.user, limit=limit), safe=True)


@require_GET
@agency_required
@cache_page(30)
def api_dashboard_sla_avg_resolution(request):
    days = int(request.GET.get("days") or 180)
    return JsonResponse(sla_avg_resolution_days(user=request.user, days=days), safe=True)


@require_GET
@agency_required
@cache_page(60)
def api_dashboard_companies_category(request):
    limit = int(request.GET.get("limit") or 12)
    return JsonResponse(companies_by_category(limit=limit), safe=True)


@require_GET
@agency_required
@cache_page(60)
def api_dashboard_companies_region(request):
    limit = int(request.GET.get("limit") or 10)
    return JsonResponse(companies_by_region(limit=limit), safe=True)


@require_GET
@agency_required
@cache_page(60)
def api_dashboard_companies_direction(request):
    limit = int(request.GET.get("limit") or 12)
    return JsonResponse(companies_by_direction(limit=limit), safe=True)


@require_GET
@agency_required
@cache_page(60)
def api_dashboard_data_quality(request):
    return JsonResponse(data_quality_summary(), safe=True)



@require_GET
@agency_required
def requests_list(request):
    qs = (
        Request.objects
        .select_related("company", "employee", "assigned_department", "assigned_employee")
        .prefetch_related("directions")
        .order_by("-created_at")
    )

    qs = visible_requests_qs(qs, request.user)

    bucket = (request.GET.get("bucket") or "").strip()
    if not bucket:
        return redirect(f"{request.path}?bucket=inbox")

    qs = apply_bucket(qs, request.user, bucket)

    f = PanelRequestFilterForm(request.GET or None)
    if f.is_valid():
        q = (f.cleaned_data.get("q") or "").strip()
        status = (f.cleaned_data.get("status") or "").strip()
        overdue = bool(f.cleaned_data.get("overdue"))

        if q:
            qs = qs.filter(
                Q(public_id__icontains=q) |
                Q(company__name__icontains=q) |
                Q(company__inn__icontains=q) |
                Q(description__icontains=q)
            )
        if status:
            qs = qs.filter(status=status)

        if overdue:
            today = date.today()
            qs = qs.filter(due_date__lt=today).exclude(status=Request.Status.DONE)

    items = list(qs[:200])
    today = date.today()

    for obj in items:
        # SLA по due_date
        obj.is_overdue_ui = bool(obj.due_date and obj.due_date < today and obj.status != Request.Status.DONE)
        if obj.due_date:
            delta = (obj.due_date - today).days
            if obj.status == Request.Status.DONE:
                obj.sla_label = _("Завершено")
                obj.sla_level = "ok"
            elif delta < 0:
                obj.sla_label = _("Просрочено на %(d)s дн.") % {"d": abs(delta)}
                obj.sla_level = "bad"
            elif delta == 0:
                obj.sla_label = _("Срок сегодня")
                obj.sla_level = "warn"
            elif delta <= 3:
                obj.sla_label = _("Осталось %(d)s дн.") % {"d": delta}
                obj.sla_level = "warn"
            else:
                obj.sla_label = _("Осталось %(d)s дн.") % {"d": delta}
                obj.sla_level = "ok"
        else:
            obj.sla_label = _("Без срока")
            obj.sla_level = "info"

    context = {
        "items": items,
        "today": today,
        "filter_form": f,
        "can_write": _can_write(request.user),
        "is_chancellery": _in_group(request.user, GROUP_CHANCELLERY),
        "is_deputy_assistant": _in_group(request.user, GROUP_DEPUTY_ASSISTANT),
        "is_executor": _in_group(request.user, GROUP_EXECUTOR),
        "is_directors": _in_group(request.user, GROUP_DIRECTORS),
        "is_head_of_department": _in_group(request.user, GROUP_HEAD_OF_DEPARTMENT),
        "bucket": bucket,
    }
    return render(request, "panel/requests/list.html", context)


@require_GET
@agency_required
def request_detail(request, pk: int):
    obj = get_object_or_404(
        Request.objects.select_related(
            "company", "employee", "assigned_department", "assigned_employee"
        ).prefetch_related(
            "directions", "files", "resolutions", "steps", "history"
        ),
        pk=pk
    )

    # object-level access
    visible = _filter_queryset_for_user(Request.objects.filter(pk=obj.pk), request.user).exists()
    if not visible:
        raise Http404()

    deputy_assistants = (
        Employee.objects
        .select_related("user", "department")
        .filter(user__groups__name=GROUP_DEPUTY_ASSISTANT)
        .order_by("user__username")
    )

    emp = getattr(request.user, "agency_employee", None)
    assign_form = AssignExecutorForm(department=(emp.department if emp else None))

    resolution_form = ResolutionForm()
    context = {
        "obj": obj,
        "today": date.today(),
        "step_form": StepForm(),
        "can_write": _can_write(request.user),
        "is_chancellery": _in_group(request.user, GROUP_CHANCELLERY),
        "is_deputy_assistant": _in_group(request.user, GROUP_DEPUTY_ASSISTANT),
        "is_head_of_department": _in_group(request.user, GROUP_HEAD_OF_DEPARTMENT),
        "is_executor": _in_group(request.user, GROUP_EXECUTOR),
        "departments": resolution_form.fields["target_department"].queryset,
        "employees": resolution_form.fields["target_employee"].queryset,
        "assign_form": assign_form,
    }
    return render(request, "panel/requests/detail.html", context)


def _render_detail_oob(request, obj_id: int):
    obj = Request.objects.select_related(
        "company", "employee", "assigned_department", "assigned_employee"
    ).prefetch_related("directions", "files", "resolutions", "steps", "history").get(pk=obj_id)

    deputy_assistants = (
        Employee.objects
        .select_related("user", "department")
        .filter(user__groups__name=GROUP_DEPUTY_ASSISTANT)
        .order_by("user__username")
    )

    resolution_form = ResolutionForm()
    context = {
        "obj": obj,
        "today": date.today(),
        "resolution_form": resolution_form,
        "step_form": StepForm(),
        "can_write": _can_write(request.user),
        "is_chancellery": _in_group(request.user, GROUP_CHANCELLERY),
        "is_deputy_assistant": _in_group(request.user, GROUP_DEPUTY_ASSISTANT),
        "is_executor": _in_group(request.user, GROUP_EXECUTOR),
        "departments": resolution_form.fields["target_department"].queryset,
        "employees": resolution_form.fields["target_employee"].queryset,
        "deputy_assistants": deputy_assistants,
    }
    return render(request, "panel/requests/_detail_oob.html", context)



def _must_be(obj, user, group_name: str):
    if not _in_group(user, group_name):
        raise Http404()
    # и объект должен быть видимым пользователю (особенно важно для executor)
    visible = _filter_queryset_for_user(Request.objects.filter(pk=obj.pk), user).exists()
    if not visible:
        raise Http404()


def _render_fragments(request, obj_id: int):
    obj = Request.objects.select_related(
        "company", "employee", "assigned_department", "assigned_employee"
    ).prefetch_related("directions", "files", "resolutions", "steps", "history").get(pk=obj_id)

    deputy_assistants = (
        Employee.objects
        .select_related("user", "department")
        .filter(user__groups__name=GROUP_DEPUTY_ASSISTANT)
        .order_by("user__username")
    )

    resolution_form = ResolutionForm()
    context = {
        "obj": obj,
        "today": date.today(),
        "resolution_form": resolution_form,
        "step_form": StepForm(),
        "can_write": _can_write(request.user),
        "is_chancellery": _in_group(request.user, GROUP_CHANCELLERY),
        "is_deputy_assistant": _in_group(request.user, GROUP_DEPUTY_ASSISTANT),
        "is_executor": _in_group(request.user, GROUP_EXECUTOR),
        "departments": resolution_form.fields["target_department"].queryset,
        "employees": resolution_form.fields["target_employee"].queryset,
        "deputy_assistants": deputy_assistants
    }
    return render(request, "panel/requests/_fragments.html", context)


@require_POST
@agency_required
def request_action_add_step(request, pk: int):
    obj = get_object_or_404(Request, pk=pk)
    _must_be(obj, request.user, GROUP_EXECUTOR)

    if obj.status == Request.Status.DONE:
        messages.warning(request, _("Нельзя добавлять шаги: обращение уже завершено."))
        if _is_htmx(request):
            return _render_detail_oob(request, obj.pk)
        return redirect("panel:request_detail", pk=obj.pk)

    form = StepForm(request.POST)
    if not form.is_valid():
        messages.error(request, _("Проверьте форму шага: есть ошибки."))
        if _is_htmx(request):
            return _render_detail_oob(request, obj.pk)
        return redirect("panel:request_detail", pk=obj.pk)

    add_step(
        request=obj,
        author=request.user,
        text=form.cleaned_data["text"],
        comment=_("Шаг добавлен из панели"),
    )

    messages.success(request, _("Шаг добавлен."))
    if _is_htmx(request):
        return _render_detail_oob(request, obj.pk)
    return redirect("panel:request_detail", pk=obj.pk)



@require_POST
@agency_required
def request_action_mark_done(request, pk: int):
    obj = get_object_or_404(Request, pk=pk)
    _must_be(obj, request.user, GROUP_EXECUTOR)

    if obj.status == Request.Status.DONE:
        messages.info(request, _("Уже завершено."))
        if _is_htmx(request):
            return _render_detail_oob(request, obj.pk)
        return redirect("panel:request_detail", pk=obj.pk)

    mark_done(request=obj, actor=request.user, comment=_("Завершено из панели"))
    messages.success(request, _("Обращение завершено."))
    if _is_htmx(request):
        return _render_detail_oob(request, obj.pk)
    return redirect("panel:request_detail", pk=obj.pk)


@require_POST
@agency_required
def request_action_assign_executor(request, pk: int):
    obj = get_object_or_404(Request, pk=pk)
    _must_be(obj, request.user, GROUP_HEAD_OF_DEPARTMENT)

    emp = getattr(request.user, "agency_employee", None)
    if not emp or not emp.department_id:
        raise Http404()

    # объект должен быть из его департамента
    if obj.assigned_department_id != emp.department_id:
        raise Http404()

    form = AssignExecutorForm(request.POST, department=emp.department)
    if not form.is_valid():
        messages.error(request, _("Проверьте форму назначения исполнителя."))
        if _is_htmx(request):
            return _render_detail_oob(request, obj.pk)
        return redirect("panel:request_detail", pk=obj.pk)

    assign_executor(
        request=obj,
        actor=request.user,
        target_employee=form.cleaned_data["target_employee"],
        due_date=form.cleaned_data["due_date"],
        comment=_("Назначено начальником департамента"),
    )

    messages.success(request, _("Исполнитель назначен."))
    if _is_htmx(request):
        return _render_detail_oob(request, obj.pk)
    return redirect("panel:request_detail", pk=obj.pk)


@require_POST
@agency_required
def request_action_set_waiting(request, pk: int):
    obj = get_object_or_404(Request, pk=pk)

    # доступ: executor (свои) или head_of_department (свой департамент)
    emp = getattr(request.user, "agency_employee", None)
    if not emp:
        raise Http404()

    is_executor = _in_group(request.user, GROUP_EXECUTOR)
    is_head = _in_group(request.user, GROUP_HEAD_OF_DEPARTMENT)

    if is_executor:
        if obj.assigned_employee_id != emp.id:
            raise Http404()
    elif is_head:
        if obj.assigned_department_id != emp.department_id:
            raise Http404()
    else:
        raise Http404()

    set_waiting(request=obj, actor=request.user, comment=_("Ожидаем ответ/информацию"))
    messages.success(request, _("Статус: ожидает ответа."))
    if _is_htmx(request):
        return _render_detail_oob(request, obj.pk)
    return redirect("panel:request_detail", pk=obj.pk)


@require_POST
@agency_required
def request_action_set_in_progress(request, pk: int):
    obj = get_object_or_404(Request, pk=pk)

    emp = getattr(request.user, "agency_employee", None)
    if not emp:
        raise Http404()

    is_executor = _in_group(request.user, GROUP_EXECUTOR)
    is_head = _in_group(request.user, GROUP_HEAD_OF_DEPARTMENT)

    if is_executor:
        if obj.assigned_employee_id != emp.id:
            raise Http404()
    elif is_head:
        if obj.assigned_department_id != emp.department_id:
            raise Http404()
    else:
        raise Http404()

    set_in_progress(request=obj, actor=request.user, comment=_("Работа продолжена"))
    messages.success(request, _("Статус: в работе."))
    if _is_htmx(request):
        return _render_detail_oob(request, obj.pk)
    return redirect("panel:request_detail", pk=obj.pk)
