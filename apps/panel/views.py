from django.views.decorators.http import require_GET
from django.shortcuts import render
from apps.users.decorators import agency_required


@require_GET
@agency_required
def dashboard(request):
    # пока пустой "общий" дашборд. Дальше сюда перенесём метрики по обращениям/компаниям/телефонии.
    return render(request, "panel/dashboard.html")
