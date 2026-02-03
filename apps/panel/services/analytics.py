# apps/panel/services/analytics.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

from django.contrib.auth.models import Group
from django.db.models import (
    Avg,
    Case,
    Count,
    DurationField,
    ExpressionWrapper,
    F,
    IntegerField,
    Q,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone

from apps.companies.models import Company, Category, Direction, Region
from apps.requests.models import Request


# --- Роли (как у тебя в panel/views.py) ---
GROUP_CHANCELLERY = "chancellery"
GROUP_DEPUTY_ASSISTANT = "deputy_assistant"
GROUP_EXECUTOR = "executor"
GROUP_DIRECTORS = "directors"


# -----------------------------
# Helpers
# -----------------------------
def _today() -> date:
    return timezone.localdate()


def _now() -> datetime:
    return timezone.localtime()


def _days_ago(n: int) -> datetime:
    return _now() - timedelta(days=int(n))


def _in_group(user, name: str) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return user.groups.filter(name=name).exists()


def filter_requests_for_user(qs, user):
    """
    Повторяем ту же логику видимости, что у тебя в panel/views.py:
    - chancellery: всё
    - deputy_assistant: только где deputy_assistant = emp
    - executor: только по своему департаменту (assigned_department=emp.department)

    Важно: аналитика тоже должна уважать права доступа.
    """
    if _in_group(user, GROUP_CHANCELLERY):
        return qs

    if _in_group(user, GROUP_DIRECTORS):
        return qs

    if _in_group(user, GROUP_DEPUTY_ASSISTANT):
        emp = getattr(user, "agency_employee", None)
        if not emp:
            return qs.none()
        return qs.filter(deputy_assistant=emp)

    emp = getattr(user, "agency_employee", None)
    if not emp or not emp.department_id:
        return qs.none()
    return qs.filter(assigned_department=emp.department)


def _base_requests_qs(user=None):
    qs = (
        Request.objects
        .select_related("company", "assigned_department", "assigned_employee")
        .prefetch_related("directions")
        .all()
    )
    if user is not None:
        qs = filter_requests_for_user(qs, user)
    return qs


def _base_companies_qs():
    return (
        Company.objects
        .select_related("category", "region", "district")
        .prefetch_related("directions")
        .all()
    )


def _echarts_pie(items: Iterable[Tuple[str, int]]) -> List[Dict[str, Any]]:
    # ECharts pie expects: [{name: '...', value: 10}, ...]
    return [{"name": name, "value": int(val)} for name, val in items]


def _echarts_bar(items: Iterable[Tuple[str, int]]) -> Dict[str, List[Any]]:
    # ECharts bar/line expects: {labels: [...], values: [...]}
    labels: List[str] = []
    values: List[int] = []
    for name, val in items:
        labels.append(str(name))
        values.append(int(val))
    return {"labels": labels, "values": values}


def _echarts_time_series(items: Iterable[Tuple[date, int]]) -> Dict[str, List[Any]]:
    labels: List[str] = []
    values: List[int] = []
    for d, val in items:
        if not d:
            continue
        labels.append(d.isoformat())
        values.append(int(val))
    return {"labels": labels, "values": values}


# -----------------------------
# KPI (карточки)
# -----------------------------
def get_kpi(*, user=None) -> Dict[str, Any]:
    """
    KPI верхнего уровня: быстро понять "что происходит".
    Возвращаем компактный dict, который удобно рендерить в карточки.
    """
    today = _today()

    req_qs = _base_requests_qs(user=user)
    comp_qs = _base_companies_qs()

    # --- Requests KPI ---
    total_requests = req_qs.count()

    by_status = dict(
        req_qs.values_list("status")
        .annotate(c=Count("id"))
        .values_list("status", "c")
    )

    overdue_count = (
        req_qs.filter(due_date__lt=today)
        .exclude(status=Request.Status.DONE)
        .count()
    )

    done_today = req_qs.filter(status=Request.Status.DONE, resolved_at__date=today).count()
    new_requests = by_status.get(Request.Status.NEW, 0)
    in_progress = by_status.get(Request.Status.IN_PROGRESS, 0)
    assigned = by_status.get(Request.Status.ASSIGNED, 0)
    registered = by_status.get(Request.Status.REGISTERED, 0)

    # --- Companies KPI ---
    total_companies = comp_qs.count()
    with_region = comp_qs.filter(region__isnull=False).count()
    without_region = total_companies - with_region

    without_category = comp_qs.filter(category__isnull=True).count()
    without_directions = comp_qs.filter(directions__isnull=True).distinct().count()

    return {
        "today": today.isoformat(),
        "requests": {
            "total": total_requests,
            "new": int(new_requests),
            "registered": int(registered),
            "assigned": int(assigned),
            "in_progress": int(in_progress),
            "overdue": int(overdue_count),
            "done_today": int(done_today),
        },
        "companies": {
            "total": int(total_companies),
            "with_region": int(with_region),
            "without_region": int(without_region),
            "without_category": int(without_category),
            "without_directions": int(without_directions),
        },
    }


# -----------------------------
# Charts: Requests
# -----------------------------
def requests_by_status(*, user=None) -> Dict[str, Any]:
    """
    Donut/Pie: распределение обращений по статусам.
    """
    qs = _base_requests_qs(user=user)

    rows = (
        qs.values("status")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")
    )

    # Чтобы на фронте не гадали, отдаём label и key
    status_label = {s.value: str(s.label) for s in Request.Status}

    items = [(status_label.get(r["status"], r["status"]), r["cnt"]) for r in rows]
    return {
        "series": _echarts_pie(items),
        "raw": [{"status": r["status"], "label": status_label.get(r["status"], r["status"]), "count": int(r["cnt"])} for r in rows],
    }


def requests_by_direction(*, user=None, limit: int = 12) -> Dict[str, Any]:
    """
    Bar: топ направлений по количеству обращений.
    """
    qs = _base_requests_qs(user=user)

    rows = (
        qs.values("directions__title")
        .annotate(cnt=Count("id", distinct=True))
        .exclude(directions__title__isnull=True)
        .order_by("-cnt")
    )

    items = [(r["directions__title"], r["cnt"]) for r in rows[: int(limit)]]
    return _echarts_bar(items)


def requests_by_region(*, user=None, limit: int = 10) -> Dict[str, Any]:
    """
    Horizontal bar: топ регионов по количеству обращений.
    Регион берём от компании обращения.
    """
    qs = _base_requests_qs(user=user)

    rows = (
        qs.values("company__region__name")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")
    )

    items = []
    for r in rows:
        name = r["company__region__name"] or "— Без региона"
        items.append((name, r["cnt"]))

    return _echarts_bar(items[: int(limit)])


def requests_timeline_created(*, user=None, days: int = 30) -> Dict[str, Any]:
    """
    Line: сколько обращений создавали по дням за последние N дней.
    """
    qs = _base_requests_qs(user=user).filter(created_at__gte=_days_ago(days))

    rows = (
        qs.annotate(d=TruncDate("created_at"))
        .values("d")
        .annotate(cnt=Count("id"))
        .order_by("d")
    )
    items = [(r["d"], r["cnt"]) for r in rows]
    return _echarts_time_series(items)


def requests_timeline_done(*, user=None, days: int = 30) -> Dict[str, Any]:
    """
    Line: сколько обращений закрывали по дням за последние N дней.
    """
    qs = (
        _base_requests_qs(user=user)
        .filter(status=Request.Status.DONE, resolved_at__isnull=False, resolved_at__gte=_days_ago(days))
    )

    rows = (
        qs.annotate(d=TruncDate("resolved_at"))
        .values("d")
        .annotate(cnt=Count("id"))
        .order_by("d")
    )
    items = [(r["d"], r["cnt"]) for r in rows]
    return _echarts_time_series(items)


def sla_overdue_by_department(*, user=None, limit: int = 10) -> Dict[str, Any]:
    """
    Bar: просроченные обращения по департаментам.
    """
    today = _today()
    qs = (
        _base_requests_qs(user=user)
        .filter(due_date__lt=today)
        .exclude(status=Request.Status.DONE)
    )

    rows = (
        qs.values("assigned_department__name")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")
    )

    items = []
    for r in rows:
        name = r["assigned_department__name"] or "— Не назначено"
        items.append((name, r["cnt"]))

    return _echarts_bar(items[: int(limit)])


def sla_avg_resolution_days(*, user=None, days: int = 180) -> Dict[str, Any]:
    """
    KPI/SLA: среднее время (в днях) от создания до resolved_at для завершённых.
    """
    qs = (
        _base_requests_qs(user=user)
        .filter(status=Request.Status.DONE, resolved_at__isnull=False, created_at__gte=_days_ago(days))
    )

    # duration = resolved_at - created_at
    duration_expr = ExpressionWrapper(F("resolved_at") - F("created_at"), output_field=DurationField())
    agg = qs.aggregate(avg_duration=Avg(duration_expr), done_cnt=Count("id"))

    avg_duration = agg["avg_duration"]
    avg_days = None
    if avg_duration is not None:
        avg_days = round(avg_duration.total_seconds() / 86400.0, 2)

    return {
        "done_count": int(agg["done_cnt"] or 0),
        "avg_days": avg_days,
    }


# -----------------------------
# Charts: Companies
# -----------------------------
def companies_by_category(*, limit: int = 12) -> Dict[str, Any]:
    """
    Bar: компании по категориям (primary category).
    """
    qs = _base_companies_qs()

    rows = (
        qs.values("category__name")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")
    )

    items = []
    for r in rows:
        name = r["category__name"] or "— Без категории"
        items.append((name, r["cnt"]))

    return _echarts_bar(items[: int(limit)])


def companies_by_region(*, limit: int = 14) -> Dict[str, Any]:
    """
    Bar: компании по регионам.
    """
    qs = _base_companies_qs()

    rows = (
        qs.values("region__name")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")
    )

    items = []
    for r in rows:
        name = r["region__name"] or "— Без региона"
        items.append((name, r["cnt"]))

    return _echarts_bar(items[: int(limit)])


def companies_by_direction(*, limit: int = 12) -> Dict[str, Any]:
    """
    Bar: топ направлений по количеству компаний (M2M).
    """
    qs = _base_companies_qs()

    rows = (
        qs.values("directions__title")
        .annotate(cnt=Count("id", distinct=True))
        .exclude(directions__title__isnull=True)
        .order_by("-cnt")
    )

    items = [(r["directions__title"], r["cnt"]) for r in rows[: int(limit)]]
    return _echarts_bar(items)


def data_quality_summary() -> Dict[str, Any]:
    """
    KPI "качество данных" по компаниям:
    где у нас дырки, которые потом убьют аналитику.
    """
    qs = _base_companies_qs()
    total = qs.count()

    missing_region = qs.filter(region__isnull=True).count()
    missing_district = qs.filter(district__isnull=True).count()
    missing_category = qs.filter(category__isnull=True).count()
    missing_directions = qs.filter(directions__isnull=True).distinct().count()

    return {
        "total": int(total),
        "missing_region": int(missing_region),
        "missing_district": int(missing_district),
        "missing_category": int(missing_category),
        "missing_directions": int(missing_directions),
    }


# -----------------------------
# One-stop payload (удобно для dashboard)
# -----------------------------
def build_dashboard_payload(*, user=None) -> Dict[str, Any]:
    """
    Сборка всех основных блоков в один payload.
    Удобно: сначала отдаёшь это в view, дальше фронт рисует.
    """
    return {
        "kpi": get_kpi(user=user),

        # Requests charts
        "requests_by_status": requests_by_status(user=user),
        "requests_by_direction": requests_by_direction(user=user),
        "requests_by_region": requests_by_region(user=user),
        "requests_timeline_created": requests_timeline_created(user=user, days=30),
        "requests_timeline_done": requests_timeline_done(user=user, days=30),
        "sla_overdue_by_department": sla_overdue_by_department(user=user),
        "sla_avg_resolution_days": sla_avg_resolution_days(user=user, days=180),

        # Companies charts
        "companies_by_category": companies_by_category(),
        "companies_by_region": companies_by_region(),
        "companies_by_direction": companies_by_direction(),
        "data_quality": data_quality_summary(),
    }
