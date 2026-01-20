from typing import Optional, Literal
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.translation import get_language
from django.views.decorators.http import require_GET

from apps.companies.models import Company, Category, Region, District, Direction
from apps.users.decorators import agency_required

Lang = Literal["ru", "uz"]

def _resolve_lang(request: HttpRequest, url_lang: Optional[str] = None) -> Lang:
    """
    Определяем язык показа:
    1) если передан в URL (ru|uz|en) — используем его;
    2) иначе — берём активный язык из Django (LocaleMiddleware / i18n).
    """
    if url_lang in {"ru", "uz"}:
        return url_lang  # type: ignore
    lang = (get_language() or "ru").lower()
    return lang if lang in {"ru", "uz"} else "ru"  # fallback


def _company_filters_qs(request):
    qs = (
        Company.objects
        .select_related("category", "region", "district", "unit")
        .prefetch_related("phones", "directions", "employee_company__position")
        .all()
    )

    q = (request.GET.get("q") or "").strip()
    category_id = request.GET.get("category") or ""
    region_id = request.GET.get("region") or ""
    district_id = request.GET.get("district") or ""
    direction_ids = request.GET.getlist("direction")
    direction_ids = [d for d in direction_ids if d]

    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(inn__icontains=q)
            | Q(description__icontains=q)
            | Q(phones__phone__icontains=q)
            | Q(employee_company__first_name__icontains=q)
            | Q(employee_company__last_name__icontains=q)
            | Q(employee_company__middle_name__icontains=q)
        ).distinct()

    if category_id:
        qs = qs.filter(category_id=category_id)

    if region_id:
        qs = qs.filter(region_id=region_id)

    if district_id:
        qs = qs.filter(district_id=district_id)

    if direction_ids:
        qs = qs.filter(directions__id__in=direction_ids).distinct()

    return qs


@require_GET
@agency_required
def companies_page(request):
    # полная страница: фильтры + контейнер для таблицы
    context = {
        "categories": Category.objects.order_by("name"),
        "regions": Region.objects.order_by("name"),
        "directions": Direction.objects.order_by("title"),
    }
    return render(request, "companies/companies_page.html", context)


@require_GET
@agency_required
def companies_table_partial(request):
    qs = _company_filters_qs(request).order_by("name")

    paginator = Paginator(qs, 25)
    page_number = request.GET.get("page") or 1
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "paginator": paginator,
        "q": (request.GET.get("q") or "").strip(),
        "category": request.GET.get("category") or "",
        "region": request.GET.get("region") or "",
        "district": request.GET.get("district") or "",
        "direction_ids": request.GET.getlist("direction"),
    }
    return render(request, "companies/partials/companies_table.html", context)


@require_GET
def districts_by_region(request):
    """
    AJAX-эндпоинт:
    GET /district-json/?region_id=ID
    Возвращает список районов для выбранного региона.
    """
    region_id = request.GET.get("region_id")
    if not region_id:
        return JsonResponse({"results": []})

    try:
        region_id_int = int(region_id)
    except (TypeError, ValueError):
        return JsonResponse({"results": []})

    lang = _resolve_lang(request)

    districts_qs = (
        District.objects
        .filter(region_id=region_id_int)
        .order_by("code", "id")
    )

    results = []
    for s in districts_qs:
        name = s.name

        results.append({
            "id": s.id,
            "name": name,
        })

    return JsonResponse({"results": results})
