# apps/requests/services.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import (
    Request,
    RequestHistory,
    RequestResolution,
    RequestStep,
    RequestCounter,
)
from apps.agency.models import Department, Employee as AgencyEmployee


@dataclass(frozen=True)
class ServiceResult:
    request: Request

def _add_history(
    *,
    request: Request,
    actor,
    action: str,
    comment: str = "",
    from_status: str = "",
    to_status: str = "",
) -> RequestHistory:
    return RequestHistory.objects.create(
        request=request,
        actor=actor if actor and getattr(actor, "pk", None) else None,
        action=action,
        comment=comment or "",
        from_status=from_status or "",
        to_status=to_status or "",
    )


def _set_status(*, request: Request, actor, new_status: str, comment: str = "") -> None:
    old = request.status
    if old == new_status:
        # не шумим лишний раз
        return

    request.status = new_status
    request.save(update_fields=["status", "updated_at"])
    _add_history(
        request=request,
        actor=actor,
        action=RequestHistory.Action.STATUS_CHANGED,
        comment=comment,
        from_status=old,
        to_status=new_status,
    )

def _format_public_id(year: int, seq: int) -> str:
    return f"{year}-{seq:06d}"

@transaction.atomic
def ensure_public_id(*, request: Request) -> Request:
    """
    Генерит public_id если его нет.
    Делает это через RequestCounter + select_for_update(), чтобы не было гонок.
    """
    if request.public_id:
        return request

    year = timezone.now().year

    counter, _ = RequestCounter.objects.select_for_update().get_or_create(year=year)
    counter.last_number += 1
    counter.save(update_fields=["last_number"])

    seq = counter.last_number
    request.public_year = year
    request.public_seq = seq
    request.public_id = _format_public_id(year, seq)
    request.save(update_fields=["public_year", "public_seq", "public_id", "updated_at"])

    return request


@transaction.atomic
def create_public_request(
    *,
    company,
    employee,
    description: str,
    directions=None,
    attachments=None,
) -> Request:
    """
    Единая точка создания обращения из публичной формы:
    - создаём Request
    - генерим public_id
    - сохраняем направления и вложения (если есть)
    - пишем историю CREATED
    """
    req = Request.objects.create(
        company=company,
        employee=employee,
        description=description,
    )

    ensure_public_id(request=req)

    if directions is not None:
        req.directions.set(directions)

    # attachments создаются в view сейчас вручную, можно перенести сюда, если хочешь.
    # Тогда просто пробрось attachments и создай RequestFile внутри сервиса.

    _add_history(
        request=req,
        actor=None,  # публичный пользователь не в системе
        action=RequestHistory.Action.CREATED,
        comment=_("Обращение создано через публичную форму"),
        from_status="",
        to_status=req.status,
    )
    return req

@transaction.atomic
def register_request(*, request: Request, actor, comment: str = "") -> ServiceResult:
    """
    Канцелярия зарегистрировала обращение.
    """
    old = request.status
    request.status = Request.Status.REGISTERED
    request.save(update_fields=["status", "updated_at"])
    _add_history(
        request=request,
        actor=actor,
        action=RequestHistory.Action.REGISTERED,
        comment=comment,
        from_status=old,
        to_status=request.status,
    )
    return ServiceResult(request=request)


@transaction.atomic
def send_for_resolution(*, request: Request, actor, deputy_assistant: Optional[AgencyEmployee] = None, comment: str = "") -> ServiceResult:
    """
    Канцелярия отправляет на резолюцию + фиксирует кому отправили (помощнику руководителя).
    """
    old = request.status

    if deputy_assistant is not None:
        request.deputy_assistant = deputy_assistant

    request.status = Request.Status.SENT_FOR_RESOLUTION
    request.save(update_fields=["status", "deputy_assistant", "updated_at"])

    _add_history(
        request=request,
        actor=actor,
        action=RequestHistory.Action.SENT_FOR_RESOLUTION,
        comment=comment,
        from_status=old,
        to_status=request.status,
    )
    return ServiceResult(request=request)



@transaction.atomic
def create_resolution(
    *,
    request: Request,
    author,
    text: str,
    target_department: Optional[Department] = None,
    target_employee: Optional[AgencyEmployee] = None,
    due_date=None,
    comment: str = "",
    auto_set_assigned: bool = True,
) -> ServiceResult:
    """
    Помощник замдиректора ставит резолюцию.
    Синхронизируем Request.assigned_* и due_date.
    """

    # Небольшая “защита от людей”:
    # если указали сотрудника, но департамент не указали, подтянем из профиля.
    if target_employee and not target_department:
        target_department = target_employee.department

    resolution = RequestResolution.objects.create(
        request=request,
        author=author,
        text=text,
        target_department=target_department,
        target_employee=target_employee,
        due_date=due_date,
    )

    # Обновляем кэш-поля на Request (чтобы списки в админке были быстрыми)
    if auto_set_assigned:
        update_fields = ["updated_at"]
        if target_department:
            request.assigned_department = target_department
            update_fields.append("assigned_department")
        if target_employee:
            request.assigned_employee = target_employee
            update_fields.append("assigned_employee")
        if due_date:
            request.due_date = due_date
            update_fields.append("due_date")

        # статус: после резолюции логично "ASSIGNED" (если есть куда назначать)
        old = request.status
        if target_department or target_employee:
            request.status = Request.Status.ASSIGNED
            update_fields.append("status")

        request.save(update_fields=update_fields)

        _add_history(
            request=request,
            actor=author,
            action=RequestHistory.Action.RESOLVED,
            comment=comment or _("Резолюция добавлена"),
            from_status=old,
            to_status=request.status,
        )

        if target_department or target_employee:
            _add_history(
                request=request,
                actor=author,
                action=RequestHistory.Action.ASSIGNED,
                comment=_("Назначено: департамент=%(dep)s, сотрудник=%(emp)s") % {
                    "dep": target_department.name if target_department else "-",
                    "emp": str(target_employee) if target_employee else "-",
                },
                from_status="",
                to_status="",
            )
    else:
        _add_history(
            request=request,
            actor=author,
            action=RequestHistory.Action.RESOLVED,
            comment=comment or _("Резолюция добавлена (без изменения назначения в обращении)"),
        )

    return ServiceResult(request=request)


@transaction.atomic
def add_step(*, request: Request, author, text: str, comment: str = "") -> ServiceResult:
    if request.status == Request.Status.DONE:
        # тихо и без истерики: просто не даём добавлять
        return ServiceResult(request=request)
    RequestStep.objects.create(request=request, author=author, text=text)

    _add_history(
        request=request,
        actor=author,
        action=RequestHistory.Action.STEP_ADDED,
        comment=comment or _("Добавлен шаг работы"),
    )

    # Если шаг добавили, логично перевести в IN_PROGRESS (если ещё не)
    if request.status in {Request.Status.ASSIGNED, Request.Status.SENT_FOR_RESOLUTION, Request.Status.REGISTERED}:
        _set_status(request=request, actor=author, new_status=Request.Status.IN_PROGRESS, comment=_("Начата работа"))

    return ServiceResult(request=request)


@transaction.atomic
def mark_done(*, request: Request, actor, comment: str = "") -> ServiceResult:
    old = request.status
    request.status = Request.Status.DONE
    request.resolved_at = timezone.now()
    request.save(update_fields=["status", "resolved_at", "updated_at"])

    _add_history(
        request=request,
        actor=actor,
        action=RequestHistory.Action.DONE,
        comment=comment or _("Обращение обработано"),
        from_status=old,
        to_status=request.status,
    )
    return ServiceResult(request=request)
