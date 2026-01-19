from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from .models import TelephonyLink
from .services import fetch_kerio_users_with_numbers, pull_sync_kerio_links, provision_employee_to_kerio, \
    build_directory_rows
from ..users.decorators import agency_required


@require_POST
@agency_required
def pull_sync(request):
    res = pull_sync_kerio_links()
    messages.success(request, f"Синхронизация Kerio завершена. Обновлено: {res['updated']}")
    return redirect("telephony:directory_page")


@require_POST
@agency_required
def push_create_user(request, link_id: int):
    link = get_object_or_404(TelephonyLink, pk=link_id)

    if link.kerio_guid:
        messages.info(request, "Уже привязан к Kerio (GUID есть).")
        return redirect("telephony:directory_page")

    try:
        out = provision_employee_to_kerio(link)
        messages.success(request, f"Создан в Kerio. GUID: {out.get('kerio_guid')}")
    except Exception as e:
        messages.error(request, f"Ошибка Kerio provision: {e}")

    return redirect("telephony:directory_page")


@require_GET
@agency_required
def kerio_numbers_api(request):
    items = fetch_kerio_users_with_numbers()

    show_disabled = request.GET.get("show_disabled") == "1"
    if not show_disabled:
        items = [x for x in items if not x["disabled"]]

    only_with_numbers = request.GET.get("only_with_numbers") == "1"
    if only_with_numbers:
        items = [x for x in items if x["numbers"]]

    return JsonResponse({"count": len(items), "items": items})


@require_GET
@agency_required
def directory_page(request):
    items = build_directory_rows()
    return render(request, "telephony/directory.html", {"items": items})

@require_GET
@agency_required
def directory_table(request):
    items = build_directory_rows()
    return render(request, "telephony/_directory_table.html", {"items": items})
