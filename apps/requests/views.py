import secrets
from django.http import Http404, JsonResponse, HttpResponse
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET

from apps.companies.models import Company, EmployeeCompany, Position, Direction, Region, District, Category
from .models import Request, RequestFile, RequestHistory
from .forms import PublicRequestForm, TrackRequestsForm
from .services import create_public_request
from ..users.decorators import public_company_only


@transaction.atomic
@public_company_only
def public_request_create(request):
    district_qs = District.objects.none()
    if request.method == "POST":

        region_id = request.POST.get("region")
        if region_id and str(region_id).isdigit():
            district_qs = District.objects.filter(region_id=int(region_id)).order_by("name")

        form = PublicRequestForm(
            request.POST,
            request.FILES,
            directions_qs=Direction.objects.all(),
            district_qs=district_qs,
        )

        if form.is_valid():
            inn = form.cleaned_data["inn"].strip()
            company_name = form.cleaned_data["company_name"].strip()

            chosen_cat = form.cleaned_data["category"]

            company, _created = Company.objects.get_or_create(
                inn=inn,
                defaults={
                    "name": company_name,
                    "category": chosen_cat,
                    "region": form.cleaned_data.get("region"),
                    "district": form.cleaned_data.get("district"),
                }
            )

            updated = False
            new_region = form.cleaned_data.get("region")
            new_district = form.cleaned_data.get("district")

            if company.region_id != (new_region.id if new_region else None):
                company.region = new_region
                updated = True

            if company.district_id != (new_district.id if new_district else None):
                company.district = new_district
                updated = True

            if company.name != company_name and company_name:
                company.name = company_name
                updated = True

            # обновляем primary category (если разрешаешь)
            if company.category_id != chosen_cat.id:
                company.category = chosen_cat
                updated = True

            if updated:
                company.save()

            company.categories.add(chosen_cat)

            dirs = form.cleaned_data.get("directions")
            if dirs:
                company.directions.add(*dirs)

            # 3) employee
            employee = (
                EmployeeCompany.objects
                .filter(
                    company=company,
                    first_name=form.cleaned_data["first_name"].strip(),
                    last_name=form.cleaned_data["last_name"].strip(),
                    middle_name=(form.cleaned_data.get("middle_name") or "").strip() or None,
                )
                .first()
            )

            if employee is None:
                employee = EmployeeCompany.objects.create(
                    company=company,
                    first_name=form.cleaned_data["first_name"].strip(),
                    last_name=form.cleaned_data["last_name"].strip(),
                    middle_name=(form.cleaned_data.get("middle_name") or "").strip() or None,
                    phone=(form.cleaned_data.get("phone") or "").strip() or None,
                    email=(form.cleaned_data.get("email") or "").strip() or None,
                )
            else:
                # обновляем ТОЛЬКО если в базе пусто (не ломаем существующие данные)
                updated = False
                new_phone = (form.cleaned_data.get("phone") or "").strip() or None
                new_email = (form.cleaned_data.get("email") or "").strip() or None

                if not employee.phone and new_phone:
                    employee.phone = new_phone
                    updated = True

                if not employee.email and new_email:
                    employee.email = new_email
                    updated = True

                # на всякий: если middle_name был пустой, а теперь пришёл
                new_middle = (form.cleaned_data.get("middle_name") or "").strip() or None
                if not employee.middle_name and new_middle:
                    employee.middle_name = new_middle
                    updated = True

                if updated:
                    employee.save(update_fields=["phone", "email", "middle_name"])


            # 4) request
            req = create_public_request(
                company=company,
                employee=employee,
                description=form.cleaned_data["description"],
                directions=form.cleaned_data["directions"],
            )

            request.session["adli_public_id"] = req.public_id

            # 5) attachments
            for f in form.cleaned_data.get("attachments", []):
                RequestFile.objects.create(request=req, file=f)

            # 6) success token (одноразовый)
            token = secrets.token_urlsafe(16)
            request.session["adli_success_token"] = token

            messages.success(request, _("Обращение отправлено. Спасибо!"))
            return redirect("requests:public_request_success", token=token)
        else:
            messages.error(request, _("Проверьте форму: есть ошибки."))
    else:
        form = PublicRequestForm(
            directions_qs=Direction.objects.all(),
            district_qs=District.objects.none(),
        )

    context = {
        "form": form,
        "categories": Category.objects.order_by("name"),
        "regions": Region.objects.order_by("name"),
    }
    return render(request, "public/request_form.html", context)


@public_company_only
def public_request_success(request, token: str):
    session_token = request.session.get("adli_success_token")
    if not session_token or session_token != token:
        raise Http404()

    public_id = request.session.get("adli_public_id")

    # одноразовость: удаляем токен после открытия success
    try:
        del request.session["adli_success_token"]
    except KeyError:
        pass

    try:
        del request.session["adli_public_id"]
    except KeyError:
        pass

    return render(request, "public/request_success.html", {"public_id": public_id})


@public_company_only
def public_track_requests(request):
    """
    Ввод inn + public_id -> показываем обращение этого сотрудника
    ТОЛЬКО если компания сотрудника совпадает по INN и по public_id.
    """
    form = TrackRequestsForm(request.POST or None)
    requests_list = []
    company = None
    not_found = False

    if request.method == "POST" and form.is_valid():
        inn = form.cleaned_data["inn"].strip()
        public_id = form.cleaned_data["public_id"].strip()

        requests_list = (
            Request.objects
            .select_related("company", "employee", "assigned_department", "assigned_employee")
            .filter(company__inn=inn, public_id=public_id)
        )

        if not requests_list.exists():
            not_found = True
        else:
            company = requests_list.first().company

    return render(
        request,
        "public/track_requests.html",
        {
            "form": form,
            "company": company,
            "requests_list": requests_list,
            "not_found": not_found,
        },
    )


@public_company_only
def public_request_history_json(request, public_id: str):
    """
    Возвращаем историю по обращению для модалки.
    ВАЖНО: показываем только “безопасные” события (статусы).
    """

    inn = (request.GET.get("inn") or "").strip()
    if not inn:
        raise Http404()

    try:
        req = Request.objects.get(public_id=public_id, company__inn=inn)
    except Request.DoesNotExist:
        raise Http404()

    # Пока безопасно отдаём только смену статуса и DONE + REGISTERED/SENT/RESOLVED/ASSIGNED.
    allowed = {
        RequestHistory.Action.CREATED,
        RequestHistory.Action.REGISTERED,
        RequestHistory.Action.SENT_FOR_RESOLUTION,
        RequestHistory.Action.RESOLVED,
        RequestHistory.Action.ASSIGNED,
        RequestHistory.Action.STATUS_CHANGED,
        RequestHistory.Action.DONE,
    }

    items = (
        req.history
        .filter(action__in=allowed)
        .select_related("actor")
        .order_by("-created_at")
    )

    data = []
    for h in items:
        status_map = {s.value: str(s.label) for s in Request.Status}

        comment = ""
        if h.action == RequestHistory.Action.ASSIGNED:
            # красиво: департамент + сотрудник (пока username)
            dep = req.assigned_department.name if req.assigned_department else ""
            emp = str(req.assigned_employee) if req.assigned_employee else ""
            if dep:
                comment = _("Назначено: %(dep)s") % {"dep": dep}
            if emp:
                comment = (comment + "\n" if comment else "") + _("Сотрудник: %(emp)s") % {"emp": emp}

        elif h.action == RequestHistory.Action.STATUS_CHANGED:
            fs = status_map.get(h.from_status, h.from_status)
            ts = status_map.get(h.to_status, h.to_status)
            comment = _("Статус изменён: %(a)s → %(b)s") % {"a": fs, "b": ts}

        data.append({
            "created_at": h.created_at.isoformat(),
            "action": h.get_action_display(),
            "from_status": h.from_status,
            "to_status": h.to_status,
            "comment": comment,
        })

    return JsonResponse({
        "public_id": req.public_id,
        "status": req.get_status_display(),
        "history": data
    })


def htmx_directions_by_category(request):
    """
    HTMX endpoint: возвращает HTML-блок с чекбоксами directions
    по выбранной категории. Сохраняем уже отмеченные пункты.
    """
    category_id = request.GET.get("category")  # имя поля select'а
    selected = request.GET.getlist("directions")  # уже выбранные чекбоксы

    qs = Direction.objects.filter(category__isnull=False).order_by("title")
    if category_id:
        qs = qs.filter(category_id=category_id)

    html = render_to_string(
        "partials/directions_choices.html",
        {
            "directions": qs,
            "selected": set(selected),
        },
        request=request,
    )
    return HttpResponse(html)

