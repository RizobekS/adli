# apps/requests/services.py
from __future__ import annotations

import logging

from dataclasses import dataclass
from typing import Optional

import requests as http_requests
from django.apps import apps
from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import (
    Request,
    RequestFile,
    RequestHistory,
    RequestOfficialResponse,
    RequestResolution,
    RequestStep,
    RequestCounter,
)
from apps.agency.models import Department, Employee as AgencyEmployee

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ServiceResult:
    request: Request


@dataclass(frozen=True)
class OfficialResponseResult:
    request: Request
    response: RequestOfficialResponse


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


@transaction.atomic
def set_waiting(*, request: Request, actor, comment: str = "") -> ServiceResult:
    """
    Исполнитель/начальник перевёл обращение в режим "ожидаем ответа".
    """
    if request.status == Request.Status.DONE:
        return ServiceResult(request=request)

    _set_status(
        request=request,
        actor=actor,
        new_status=Request.Status.WAITING,
        comment=comment or _("Ожидаем ответ/информацию"),
    )
    return ServiceResult(request=request)


@transaction.atomic
def set_in_progress(*, request: Request, actor, comment: str = "") -> ServiceResult:
    """
    Возвращаем обращение из WAITING обратно в IN_PROGRESS.
    """
    if request.status == Request.Status.DONE:
        return ServiceResult(request=request)

    _set_status(
        request=request,
        actor=actor,
        new_status=Request.Status.IN_PROGRESS,
        comment=comment or _("Работа возобновлена"),
    )
    return ServiceResult(request=request)


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

def _create_attachments(*, request: Request, attachments=None) -> None:
    if not attachments:
        return

    for file_obj in attachments:
        RequestFile.objects.create(
            request=request,
            kind=RequestFile.Kind.ATTACHMENT,
            file=file_obj,
        )

        _add_history(
            request=request,
            actor=None,
            action=RequestHistory.Action.FILE_ADDED,
            comment=_("Добавлен файл"),
        )


@transaction.atomic
def create_request_from_channel(
    *,
    company,
    employee,
    description: str,
    problem_direction=None,
    directions=None,
    attachments=None,
    source: str = Request.Source.PUBLIC_WEB,
    actor=None,
    created_comment: str = "",
) -> Request:
    """
    Универсальная точка создания обращения из любого канала:
    - public_web
    - telegram
    - admin_panel

    Логика:
    - создаём Request
    - определяем департамент по problem_direction
    - генерируем public_id
    - сохраняем направления
    - сохраняем вложения
    - пишем историю
    """

    dept = problem_direction.department if problem_direction else None
    initial_status = Request.Status.ASSIGNED if dept else Request.Status.NEW

    req = Request.objects.create(
        company=company,
        employee=employee,
        description=description,
        problem_direction=problem_direction,
        assigned_department=dept,
        status=initial_status,
        source=source,
    )

    ensure_public_id(request=req)

    if directions is not None:
        req.directions.set(directions)

    _create_attachments(request=req, attachments=attachments)

    if not created_comment:
        if source == Request.Source.TELEGRAM:
            created_comment = _("Обращение создано через Telegram bot")
        elif source == Request.Source.ADMIN_PANEL:
            created_comment = _("Обращение создано через админ-панель")
        else:
            created_comment = _("Обращение создано через публичную форму")

    _add_history(
        request=req,
        actor=actor,
        action=RequestHistory.Action.CREATED,
        comment=created_comment,
        from_status="",
        to_status=req.status,
    )

    _add_history(
        request=req,
        actor=actor,
        action=RequestHistory.Action.REGISTERED,
        comment=_("Зарегистрировано"),
        from_status=Request.Status.NEW,
        to_status=req.status,
    )

    if problem_direction:
        _add_history(
            request=req,
            actor=actor,
            action=RequestHistory.Action.RESOLVED,
            comment=_("Резолюция поставлена"),
            from_status="",
            to_status="",
        )

    if dept:
        _add_history(
            request=req,
            actor=actor,
            action=RequestHistory.Action.ASSIGNED,
            comment=_("Назначено: %(dep)s") % {"dep": dept.name},
            from_status="",
            to_status="",
        )

    return req


@transaction.atomic
def create_public_request(
    *,
    company,
    employee,
    description: str,
    directions=None,
    attachments=None,
) -> Request:
    return create_request_from_channel(
        company=company,
        employee=employee,
        description=description,
        directions=directions,
        attachments=attachments,
        source=Request.Source.PUBLIC_WEB,
        actor=None,
        created_comment=_("Обращение создано через публичную форму"),
    )

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
                comment=_("Назначено: %(dep)s, %(emp)s") % {
                    "dep": target_department.name if target_department else "-",
                    "emp": str(target_employee.display_name) if target_employee else "-",
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
def create_public_request_routed(
    *,
    company,
    employee,
    description: str,
    problem_direction,
    directions=None,
    attachments=None,
) -> Request:
    return create_request_from_channel(
        company=company,
        employee=employee,
        description=description,
        problem_direction=problem_direction,
        directions=directions,
        attachments=attachments,
        source=Request.Source.PUBLIC_WEB,
        actor=None,
        created_comment=_("Обращение создано через публичную форму"),
    )


@transaction.atomic
def assign_executor(*,request: Request, actor, target_employee: AgencyEmployee, due_date=None, comment: str = "",) -> ServiceResult:
    """
    Начальник департамента назначает исполнителя.
    """
    # базовые защиты
    if request.status == Request.Status.DONE:
        return ServiceResult(request=request)

    # назначаем
    request.assigned_employee = target_employee
    # на всякий случай синхронизируем департамент
    if target_employee.department_id and not request.assigned_department_id:
        request.assigned_department = target_employee.department

    update_fields = ["assigned_employee", "assigned_department", "updated_at"]
    if due_date:
        request.due_date = due_date
        update_fields.append("due_date")

    request.save(update_fields=update_fields)

    _add_history(
        request=request,
        actor=actor,
        action=RequestHistory.Action.ASSIGNED,
        comment=comment or _("Назначен исполнитель: %(emp)s") % {"emp": str(target_employee)},
    )


    if due_date:
        _add_history(
            request = request,
            actor = actor,
            action = RequestHistory.Action.OTHER,
            comment = _("Установлен срок исполнения: %(d)s") % {"d": str(due_date)},
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
    if request.status in {Request.Status.ASSIGNED, Request.Status.WAITING}:
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


def _get_request_email(request: Request) -> str:
    employee = getattr(request, "employee", None)
    email = ((getattr(employee, "email", "") or "").strip().lower())
    if email:
        return email

    telegram_profile = getattr(request, "telegram_profile", None)
    return ((getattr(telegram_profile, "email", "") or "").strip().lower())


def _find_telegram_profile_for_request(request: Request):
    TelegramProfile = apps.get_model("tg_bot", "TelegramProfile")

    profile = getattr(request, "telegram_profile", None)
    if profile and profile.is_active:
        return profile

    if request.source != Request.Source.TELEGRAM:
        return None

    qs = TelegramProfile.objects.filter(is_verified=True, is_active=True)

    if request.employee_id:
        profile = (
            qs.filter(employee_company_id=request.employee_id)
            .order_by("-updated_at")
            .first()
        )
        if profile:
            return profile

    if request.company_id:
        return (
            qs.filter(company_id=request.company_id)
            .order_by("-updated_at")
            .first()
        )

    return None


def _build_official_response_subject(request: Request) -> str:
    number = request.public_id or str(request.pk)
    return str(_("Официальный ответ по обращению № %(number)s") % {"number": number})


def _build_email_body(*, request: Request, response_text: str) -> str:
    number = request.public_id or str(request.pk)
    return "\n".join([
        str(_("Уважаемый заявитель!")),
        "",
        str(_("По вашему обращению № %(number)s направлен официальный ответ.") % {"number": number}),
        "",
        response_text.strip(),
        "",
        str(_("Проверить статус обращения можно на сайте murojaat.adli.uz.")),
    ])


def _build_telegram_body(*, request: Request, response_text: str, lang: str) -> str:
    number = request.public_id or str(request.pk)
    response_text = response_text.strip()
    if len(response_text) > 3500:
        response_text = response_text[:3497] + "..."

    if lang == "uz":
        return (
            f"Murojaatingiz bo'yicha rasmiy javob tayyorlandi.\n"
            f"Murojaat raqami: {number}\n\n"
            f"Javob:\n{response_text}"
        )

    return (
        f"По вашему обращению подготовлен официальный ответ.\n"
        f"Номер обращения: {number}\n\n"
        f"Ответ:\n{response_text}"
    )


def _send_official_response_email(response: RequestOfficialResponse) -> None:
    if not response.recipient_email:
        response.email_status = RequestOfficialResponse.DeliveryStatus.SKIPPED
        response.email_error = str(_("У заявителя нет прикрепленного email."))
        response.save(update_fields=["email_status", "email_error", "updated_at"])
        return

    try:
        message = EmailMessage(
            subject=response.subject,
            body=_build_email_body(request=response.request, response_text=response.text),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[response.recipient_email],
        )
        message.send(fail_silently=False)
    except Exception as exc:
        logger.exception("Failed to send official response email: response_id=%s", response.pk)
        response.email_status = RequestOfficialResponse.DeliveryStatus.FAILED
        response.email_error = str(exc)
        response.save(update_fields=["email_status", "email_error", "updated_at"])
        return

    response.email_status = RequestOfficialResponse.DeliveryStatus.SENT
    response.email_error = ""
    response.email_sent_at = timezone.now()
    response.save(update_fields=["email_status", "email_error", "email_sent_at", "updated_at"])


def _send_official_response_telegram(response: RequestOfficialResponse) -> None:
    profile = response.telegram_profile
    if not profile:
        response.telegram_status = RequestOfficialResponse.DeliveryStatus.SKIPPED
        response.telegram_error = str(_("Telegram профиль заявителя не найден."))
        response.save(update_fields=["telegram_status", "telegram_error", "updated_at"])
        return

    if not settings.TELEGRAM_BOT_TOKEN:
        response.telegram_status = RequestOfficialResponse.DeliveryStatus.FAILED
        response.telegram_error = "TELEGRAM_BOT_TOKEN is not configured"
        response.save(update_fields=["telegram_status", "telegram_error", "updated_at"])
        return

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": profile.chat_id,
        "text": _build_telegram_body(
            request=response.request,
            response_text=response.text,
            lang=profile.bot_language or "uz",
        ),
        "disable_web_page_preview": True,
    }

    try:
        api_response = http_requests.post(url, json=payload, timeout=10)
        api_response.raise_for_status()
        body = api_response.json()
        if not body.get("ok"):
            raise RuntimeError(body.get("description") or "Telegram API returned ok=false")
    except Exception as exc:
        logger.exception("Failed to send official response Telegram notification: response_id=%s", response.pk)
        response.telegram_status = RequestOfficialResponse.DeliveryStatus.FAILED
        response.telegram_error = str(exc)
        response.save(update_fields=["telegram_status", "telegram_error", "updated_at"])
        return

    response.telegram_status = RequestOfficialResponse.DeliveryStatus.SENT
    response.telegram_error = ""
    response.telegram_sent_at = timezone.now()
    response.save(update_fields=["telegram_status", "telegram_error", "telegram_sent_at", "updated_at"])


def _send_official_response_notifications(response: RequestOfficialResponse) -> None:
    response = (
        RequestOfficialResponse.objects
        .select_related("request", "request__employee", "telegram_profile")
        .get(pk=response.pk)
    )

    if response.email_status == RequestOfficialResponse.DeliveryStatus.PENDING:
        _send_official_response_email(response)

    response.refresh_from_db()
    if response.telegram_status == RequestOfficialResponse.DeliveryStatus.PENDING:
        _send_official_response_telegram(response)


def close_with_official_response(
    *,
    request: Request,
    actor,
    response_text: str,
) -> OfficialResponseResult:
    response_text = (response_text or "").strip()
    if not response_text:
        raise ValueError("Official response text is required")

    recipient_email = _get_request_email(request)
    telegram_profile = _find_telegram_profile_for_request(request)
    subject = _build_official_response_subject(request)

    email_status = RequestOfficialResponse.DeliveryStatus.PENDING
    email_error = ""
    if not recipient_email:
        email_status = RequestOfficialResponse.DeliveryStatus.SKIPPED
        email_error = str(_("У заявителя нет прикрепленного email."))

    telegram_status = RequestOfficialResponse.DeliveryStatus.SKIPPED
    telegram_error = ""
    if request.source == Request.Source.TELEGRAM:
        if telegram_profile:
            telegram_status = RequestOfficialResponse.DeliveryStatus.PENDING
        else:
            telegram_error = str(_("Telegram профиль заявителя не найден."))

    with transaction.atomic():
        response = RequestOfficialResponse.objects.create(
            request=request,
            author=actor,
            telegram_profile=telegram_profile,
            recipient_email=recipient_email,
            subject=subject,
            text=response_text,
            email_status=email_status,
            telegram_status=telegram_status,
            email_error=email_error,
            telegram_error=telegram_error,
        )
        _add_history(
            request=request,
            actor=actor,
            action=RequestHistory.Action.OFFICIAL_RESPONSE,
            comment=_("Официальный ответ добавлен"),
        )
        mark_done(request=request, actor=actor, comment=_("Завершено с официальным ответом"))

    _send_official_response_notifications(response)
    response.refresh_from_db()
    request.refresh_from_db()
    return OfficialResponseResult(request=request, response=response)


def create_official_response_for_closed_request(
    *,
    request: Request,
    actor,
    response_text: str,
    send_notifications: bool = True,
) -> OfficialResponseResult:
    response_text = (response_text or "").strip()
    if not response_text:
        raise ValueError("Official response text is required")

    if request.status != Request.Status.DONE:
        raise ValueError("Request must be already done")

    if request.official_responses.exists():
        raise ValueError("Request already has an official response")

    recipient_email = _get_request_email(request)
    telegram_profile = _find_telegram_profile_for_request(request)
    subject = _build_official_response_subject(request)

    email_status = RequestOfficialResponse.DeliveryStatus.PENDING
    email_error = ""
    if not recipient_email:
        email_status = RequestOfficialResponse.DeliveryStatus.SKIPPED
        email_error = str(_("У заявителя нет прикрепленного email."))

    telegram_status = RequestOfficialResponse.DeliveryStatus.SKIPPED
    telegram_error = ""
    if request.source == Request.Source.TELEGRAM:
        if telegram_profile:
            telegram_status = RequestOfficialResponse.DeliveryStatus.PENDING
        else:
            telegram_error = str(_("Telegram профиль заявителя не найден."))

    with transaction.atomic():
        response = RequestOfficialResponse.objects.create(
            request=request,
            author=actor,
            telegram_profile=telegram_profile,
            recipient_email=recipient_email,
            subject=subject,
            text=response_text,
            email_status=email_status,
            telegram_status=telegram_status,
            email_error=email_error,
            telegram_error=telegram_error,
        )
        _add_history(
            request=request,
            actor=actor,
            action=RequestHistory.Action.OFFICIAL_RESPONSE,
            comment=_("Официальный ответ добавлен"),
        )

    if send_notifications:
        _send_official_response_notifications(response)
        response.refresh_from_db()

    return OfficialResponseResult(request=request, response=response)
