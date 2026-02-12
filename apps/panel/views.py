# apps/panel/views.py
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
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
    mark_done,
)
from .forms import ResolutionForm, StepForm, PanelRequestFilterForm
from ..agency.models import Employee

from .services.analytics import (
    build_dashboard_payload,
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
    data_quality_summary,
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
    # кто может обрабатывать (любой из 3 групп)
    return (
        _in_group(user, GROUP_CHANCELLERY)
        or _in_group(user, GROUP_DEPUTY_ASSISTANT)
        or _in_group(user, GROUP_EXECUTOR)
    )


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

    qs = _filter_queryset_for_user(qs, request.user)

    bucket = (request.GET.get("bucket") or "").strip()

    if bucket == "new":
        bucket = "inbox"

    if not bucket:
        return redirect(f"{request.path}?bucket=inbox")

    if bucket == "all":
        pass

    if bucket == "inbox":
        if _in_group(request.user, GROUP_CHANCELLERY) or _in_group(request.user, GROUP_DIRECTORS):
            qs = qs.filter(status=Request.Status.NEW)

        elif _in_group(request.user, GROUP_DEPUTY_ASSISTANT):
            qs = qs.filter(status=Request.Status.SENT_FOR_RESOLUTION)

        elif _in_group(request.user, GROUP_HEAD_OF_DEPARTMENT):
            qs = qs.filter(status=Request.Status.ASSIGNED)

        elif _in_group(request.user, GROUP_EXECUTOR):
            qs = qs.filter(status=Request.Status.ASSIGNED)

        else:
            qs = qs.none()

    elif bucket == "active":
        # "в работе" (для каждой роли своё)
        if _in_group(request.user, GROUP_CHANCELLERY) or _in_group(request.user, GROUP_DIRECTORS):
            qs = qs.filter(status__in=[
                Request.Status.REGISTERED,
                Request.Status.SENT_FOR_RESOLUTION,
                Request.Status.ASSIGNED,
                Request.Status.IN_PROGRESS,
            ])

        elif _in_group(request.user, GROUP_DEPUTY_ASSISTANT):
            qs = qs.filter(status__in=[
                Request.Status.ASSIGNED,
                Request.Status.IN_PROGRESS,
            ])

        elif _in_group(request.user, GROUP_HEAD_OF_DEPARTMENT):
            qs = qs.filter(status=Request.Status.IN_PROGRESS)

        elif _in_group(request.user, GROUP_EXECUTOR):
            qs = qs.filter(status=Request.Status.IN_PROGRESS)

        else:
            qs = qs.none()

    elif bucket == "done":
        qs = qs.filter(status=Request.Status.DONE)

    elif bucket == "all":
        pass

    else:
        # неизвестный bucket → inbox
        return redirect(f"{request.path}?bucket=inbox")

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

    resolution_form = ResolutionForm()
    context = {
        "obj": obj,
        "today": date.today(),
        "resolution_form": ResolutionForm(),
        "step_form": StepForm(),
        "can_write": _can_write(request.user),
        "is_chancellery": _in_group(request.user, GROUP_CHANCELLERY),
        "is_deputy_assistant": _in_group(request.user, GROUP_DEPUTY_ASSISTANT),
        "is_executor": _in_group(request.user, GROUP_EXECUTOR),
        "departments": resolution_form.fields["target_department"].queryset,
        "employees": resolution_form.fields["target_employee"].queryset,
        "deputy_assistants": deputy_assistants,
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
def request_action_register(request, pk: int):
    obj = get_object_or_404(Request, pk=pk)
    _must_be(obj, request.user, GROUP_CHANCELLERY)

    if obj.status != Request.Status.NEW:
        messages.warning(request, _("Можно зарегистрировать только новое обращение."))
        if _is_htmx(request):
            return _render_detail_oob(request, obj.pk)
        return redirect("panel:request_detail", pk=obj.pk)

    register_request(request=obj, actor=request.user, comment=_("Действие из панели"))
    messages.success(request, _("Обращение зарегистрировано."))
    if _is_htmx(request):
        return _render_detail_oob(request, obj.pk)
    return redirect("panel:request_detail", pk=obj.pk)


@require_POST
@agency_required
def request_action_send_for_resolution(request, pk: int):
    obj = get_object_or_404(Request, pk=pk)
    _must_be(obj, request.user, GROUP_CHANCELLERY)

    # 1) если уже отправлено на резолюцию (или дальше) — не даём повторять
    if obj.status in {Request.Status.SENT_FOR_RESOLUTION, Request.Status.ASSIGNED, Request.Status.IN_PROGRESS, Request.Status.DONE}:
        messages.warning(request, _("Обращение уже отправлено на резолюцию."))
        if _is_htmx(request):
            return _render_detail_oob(request, obj.pk)
        return redirect("panel:request_detail", pk=obj.pk)

    # 2) deputy обязателен
    deputy_id = (request.POST.get("deputy_assistant") or "").strip()
    if not deputy_id:
        messages.error(request, _("Выберите помощника руководителя."))
        if _is_htmx(request):
            return _render_detail_oob(request, obj.pk)
        return redirect("panel:request_detail", pk=obj.pk)

    deputy_emp = get_object_or_404(
        Employee.objects.select_related("user", "department"),
        pk=int(deputy_id),
        user__groups__name=GROUP_DEPUTY_ASSISTANT,
    )

    # 3) если NEW — регистрируем автоматически (раз ты это хочешь)
    if obj.status == Request.Status.NEW:
        register_request(request=obj, actor=request.user, comment=_("Действие из панели"))

    # 4) отправляем
    send_for_resolution(
        request=obj,
        actor=request.user,
        deputy_assistant=deputy_emp,
        comment=_("Действие из панели"),
    )

    messages.success(request, _("Отправлено на резолюцию."))
    if _is_htmx(request):
        return _render_detail_oob(request, obj.pk)
    return redirect("panel:request_detail", pk=obj.pk)


@require_POST
@agency_required
def request_action_create_resolution(request, pk: int):
    obj = get_object_or_404(Request, pk=pk)
    _must_be(obj, request.user, GROUP_DEPUTY_ASSISTANT)

    form = ResolutionForm(request.POST)
    if not form.is_valid():
        messages.error(request, _("Проверьте форму резолюции: есть ошибки."))
        if _is_htmx(request):
            return _render_detail_oob(request, obj.pk)
        return redirect("panel:request_detail", pk=obj.pk)

    create_resolution(
        request=obj,
        author=request.user,
        text=form.cleaned_data["text"],
        target_department=form.cleaned_data.get("target_department"),
        target_employee=form.cleaned_data.get("target_employee"),
        due_date=form.cleaned_data.get("due_date"),
        comment=_("Резолюция добавлена из панели"),
    )
    messages.success(request, _("Резолюция добавлена, назначение обновлено."))
    if _is_htmx(request):
        return _render_detail_oob(request, obj.pk)
    return redirect("panel:request_detail", pk=obj.pk)


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
