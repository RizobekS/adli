from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django.conf import settings
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from apps.companies.models import Company, EmployeeCompany, Category, Region, District, Direction, CompanyPhone, Position
from apps.requests.models import Request
from apps.requests.services import create_request_from_channel
from .bot.utils.i18n import translate_request_status
from .models import TelegramProfile, TelegramChatBinding
from .selectors import (
    find_company_by_phone,
    find_employee_company_by_phone,
    get_active_notification_chats_for_department,
    get_request_detail_for_notification,
    find_company_by_inn,
    find_employee_company_by_company_and_phone,
)
from .bot.utils.phone import normalize_uz_phone


@dataclass(frozen=True)
class VerifyTelegramUserResult:
    profile: TelegramProfile
    company: Optional[Company]
    employee_company: Optional[EmployeeCompany]
    matched: bool


@dataclass(frozen=True)
class RegisterByInnResult:
    profile: TelegramProfile
    company: Company
    employee_company: EmployeeCompany
    company_created: bool


@transaction.atomic
def create_or_update_telegram_profile(
    *,
    telegram_user_id: int,
    chat_id: int,
    username: str = "",
    first_name: str = "",
    last_name: str = "",
    language_code: str = "",
    bot_language: str | None = None,
    phone: str = "",
    phone_normalized: str = "",
    email: str = "",
    company: Company | None = None,
    employee_company: EmployeeCompany | None = None,
    is_verified: bool = False,
) -> TelegramProfile:
    defaults = {
        "chat_id": chat_id,
        "username": username or "",
        "first_name": first_name or "",
        "last_name": last_name or "",
        "language_code": language_code or "",
        "phone": phone or "",
        "phone_normalized": phone_normalized or "",
        "email": (email or "").strip().lower(),
        "company": company,
        "employee_company": employee_company,
        "is_verified": is_verified,
        "is_active": True,
    }

    if bot_language:
        defaults["bot_language"] = bot_language

    profile, _ = TelegramProfile.objects.update_or_create(
        telegram_user_id=telegram_user_id,
        defaults=defaults,
    )
    return profile


@transaction.atomic
def set_telegram_profile_bot_language(
    *,
    telegram_user_id: int,
    chat_id: int,
    bot_language: str,
    username: str = "",
    first_name: str = "",
    last_name: str = "",
    language_code: str = "",
) -> TelegramProfile:
    if bot_language not in {"ru", "uz"}:
        bot_language = "uz"

    profile = TelegramProfile.objects.filter(
        telegram_user_id=telegram_user_id
    ).first()

    if profile:
        profile.chat_id = chat_id
        profile.username = username or ""
        profile.first_name = first_name or ""
        profile.last_name = last_name or ""
        profile.language_code = language_code or ""
        profile.bot_language = bot_language
        profile.is_active = True
        profile.save(update_fields=[
            "chat_id",
            "username",
            "first_name",
            "last_name",
            "language_code",
            "bot_language",
            "is_active",
            "updated_at",
        ])
        return profile

    return create_or_update_telegram_profile(
        telegram_user_id=telegram_user_id,
        chat_id=chat_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        language_code=language_code,
        bot_language=bot_language,
    )


@transaction.atomic
def set_telegram_profile_email(
    *,
    telegram_user_id: int,
    email: str,
) -> TelegramProfile:
    email = (email or "").strip().lower()

    profile = (
        TelegramProfile.objects
        .select_related("employee_company")
        .filter(telegram_user_id=telegram_user_id)
        .first()
    )

    if not profile:
        raise ValueError("Telegram profile not found")

    profile.email = email
    profile.save(update_fields=["email", "updated_at"])

    if profile.employee_company:
        profile.employee_company.email = email
        profile.employee_company.save(update_fields=["email"])

    return profile


def resolve_default_bot_language(language_code: str | None) -> str:
    code = (language_code or "").lower()
    if code.startswith("uz"):
        return "uz"
    if code.startswith("ru"):
        return "ru"
    return "uz"


@transaction.atomic
def verify_telegram_user_by_phone(
    *,
    telegram_user_id: int,
    chat_id: int,
    raw_phone: str,
    username: str = "",
    first_name: str = "",
    last_name: str = "",
    language_code: str = "",
) -> VerifyTelegramUserResult:
    normalized = normalize_uz_phone(raw_phone)

    employee_company = find_employee_company_by_phone(normalized)
    company = None

    if employee_company:
        company = employee_company.company
    else:
        company = find_company_by_phone(normalized)

    matched = company is not None

    existing_profile = TelegramProfile.objects.filter(telegram_user_id=telegram_user_id).first()
    bot_language = existing_profile.bot_language if existing_profile else resolve_default_bot_language(language_code)

    profile = create_or_update_telegram_profile(
        telegram_user_id=telegram_user_id,
        chat_id=chat_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        language_code=language_code,
        bot_language=bot_language,
        phone=raw_phone,
        phone_normalized=normalized,
        company=company,
        employee_company=employee_company,
        is_verified=matched,
    )

    return VerifyTelegramUserResult(
        profile=profile,
        company=company,
        employee_company=employee_company,
        matched=matched,
    )


@transaction.atomic
def bind_group_chat(
    *,
    chat_id: int,
    title: str = "",
    chat_type: str = TelegramChatBinding.ChatType.GROUP,
    department=None,
    is_active: bool = True,
) -> TelegramChatBinding:
    chat, _ = TelegramChatBinding.objects.update_or_create(
        chat_id=chat_id,
        defaults={
            "title": title or "",
            "chat_type": chat_type,
            "department": department,
            "is_active": is_active,
        },
    )
    return chat


def build_request_panel_url(request_obj: Request) -> str:
    return f"{settings.SITE_URL}/panel/request/{request_obj.pk}/"


def build_request_notification_text(request_obj: Request) -> str:
    company_name = str(request_obj.company)
    employee_name = str(request_obj.employee) if request_obj.employee else "-"
    problem_direction = str(request_obj.problem_direction) if request_obj.problem_direction else "-"
    department_name = str(request_obj.assigned_department) if request_obj.assigned_department else "-"
    source_label = request_obj.get_source_display() if hasattr(request_obj, "get_source_display") else request_obj.source

    return (
        f"🆕 <b>Yangi murojaat</b>\n\n"
        f"<b>Murojaat id:</b> {request_obj.public_id or request_obj.pk}\n"
        f"<b>Manbaa:</b> {source_label}\n"
        f"<b>Korxona:</b> {company_name}\n"
        f"<b>Murojaatchi:</b> {employee_name}\n"
        f"<b>Muammoli yo'nalish:</b> {problem_direction}\n"
        f"<b>Belgilangan bo'lim:</b> {department_name}\n\n"
        f"<b>Matn:</b>\n{request_obj.description}\n\n"
        f"<b>Ko'rish:</b>\n{build_request_panel_url(request_obj)}"
    )


def get_notification_chat_ids_for_request(request_obj: Request) -> list[int]:
    ids = []

    common_chats = get_active_notification_chats_for_department(None)
    ids.extend(common_chats.values_list("chat_id", flat=True))

    if request_obj.assigned_department_id:
        dept_chats = get_active_notification_chats_for_department(request_obj.assigned_department)
        ids.extend(dept_chats.values_list("chat_id", flat=True))

    return list(dict.fromkeys(ids))


def prepare_request_notification_payload(request_id: int) -> dict | None:
    request_obj = get_request_detail_for_notification(request_id)
    if not request_obj:
        return None

    return {
        "chat_ids": get_notification_chat_ids_for_request(request_obj),
        "text": build_request_notification_text(request_obj),
        "request_id": request_obj.id,
        "public_id": request_obj.public_id,
    }


@transaction.atomic
def create_request_from_telegram_profile(
    *,
    profile: TelegramProfile,
    problem_direction,
    category: Category | None,
    region: Region | None,
    district: District | None,
    directions=None,
    description: str,
    attachments=None,
):
    if not profile.company:
        raise ValueError("Telegram profile is not bound to company")

    company = profile.company
    employee_company = profile.employee_company

    updated = False

    if category and getattr(company, "category_id", None) != category.id:
        company.category = category
        updated = True

    if region and getattr(company, "region_id", None) != region.id:
        company.region = region
        updated = True

    if district and getattr(company, "district_id", None) != district.id:
        company.district = district
        updated = True

    if updated:
        company.save()

    if category and hasattr(company, "categories"):
        company.categories.add(category)

    if directions and hasattr(company, "directions"):
        company.directions.add(*directions)

    req = create_request_from_channel(
        company=company,
        employee=employee_company,
        description=description,
        problem_direction=problem_direction,
        directions=directions,
        attachments=attachments,
        source=Request.Source.TELEGRAM,
        actor=None,
        created_comment=_("Обращение создано через Telegram bot"),
    )
    return req


def format_request_short_text(request_obj: Request, lang: str = "uz") -> str:
    status_label = translate_request_status(request_obj.status, lang)
    number = request_obj.public_id or str(request_obj.pk)
    created = request_obj.created_at.strftime("%d.%m.%Y %H:%M")
    problem_direction = str(request_obj.problem_direction.name) if request_obj.problem_direction else "-"
    files_count = request_obj.files.count() if hasattr(request_obj, "files") else 0

    description = (request_obj.description or "").strip().replace("\n", " ")
    if len(description) > 90:
        description = description[:87] + "..."

    if lang == "uz":
        return (
            f"№ {number}\n"
            f"Status: {status_label}\n"
            f"Sana: {created}\n"
            f"Muammoli yo‘nalish: {problem_direction}\n"
            f"Fayllar: {files_count}\n"
            f"Matn: {description}"
        )

    return (
        f"№ {number}\n"
        f"Статус: {status_label}\n"
        f"Дата: {created}\n"
        f"Проблемное направление: {problem_direction}\n"
        f"Файлов: {files_count}\n"
        f"Текст: {description}"
    )


def _split_fio_parts(fio: str) -> tuple[str, str, str]:
    fio = " ".join((fio or "").strip().split())
    parts = fio.split()

    if not parts:
        return "", "", ""

    if len(parts) == 1:
        return parts[0], "", ""

    if len(parts) == 2:
        return parts[0], parts[1], ""

    return parts[0], parts[1], " ".join(parts[2:])


@transaction.atomic
def register_or_bind_telegram_profile_by_inn(
    *,
    telegram_user_id: int,
    chat_id: int,
    raw_phone: str,
    username: str = "",
    tg_first_name: str = "",
    tg_last_name: str = "",
    language_code: str = "",
    inn: str,
    company_name: str = "",
    fio: str = "",
    email: str = "",
    region: Region | None = None,
    district: District | None = None,
    category: Category | None = None,
    directions=None,
) -> RegisterByInnResult:
    inn = (inn or "").strip()
    normalized_phone = normalize_uz_phone(raw_phone)
    email = (email or "").strip().lower()

    if not inn:
        raise ValueError("ИНН обязателен")

    existing_company = find_company_by_inn(inn)
    company_created = False

    if existing_company:
        company = existing_company

        changed = False
        if region and not company.region_id:
            company.region = region
            changed = True
        if district and not company.district_id:
            company.district = district
            changed = True
        if category and not company.category_id:
            company.category = category
            changed = True

        if changed:
            company.save()

        if category and hasattr(company, "categories"):
            company.categories.add(category)

        if directions and hasattr(company, "directions"):
            company.directions.add(*directions)
    else:
        company = Company.objects.create(
            inn=inn,
            name=(company_name or inn).strip(),
            region=region,
            district=district,
            category=category,
            data_source=Company.DataSource.TELEGRAM,
            verification_level=Company.VerificationLevel.LOW,
        )
        company_created = True

        if category and hasattr(company, "categories"):
            company.categories.add(category)

        if directions and hasattr(company, "directions"):
            company.directions.add(*directions)

    if normalized_phone:
        CompanyPhone.objects.get_or_create(
            company=company,
            phone=normalized_phone,
            defaults={
                "kind": CompanyPhone.Kind.MOBILE,
                "is_primary": not CompanyPhone.objects.filter(company=company, is_primary=True).exists(),
            },
        )

    employee_company = find_employee_company_by_company_and_phone(company, normalized_phone)

    if not employee_company:
        first_name, last_name, middle_name = _split_fio_parts(fio)

        employee_company = EmployeeCompany.objects.create(
            company=company,
            first_name=first_name or tg_first_name or None,
            last_name=last_name or tg_last_name or None,
            middle_name=middle_name or None,
            phone=normalized_phone or None,
            email=email or None,
            position=None,
        )
    else:
        changed_fields = []

        if normalized_phone and not employee_company.phone:
            employee_company.phone = normalized_phone
            changed_fields.append("phone")

        if email and employee_company.email != email:
            employee_company.email = email
            changed_fields.append("email")

        if changed_fields:
            employee_company.save(update_fields=changed_fields)

    existing_profile = TelegramProfile.objects.filter(telegram_user_id=telegram_user_id).first()
    bot_language = existing_profile.bot_language if existing_profile else resolve_default_bot_language(language_code)

    profile = create_or_update_telegram_profile(
        telegram_user_id=telegram_user_id,
        chat_id=chat_id,
        username=username,
        first_name=tg_first_name,
        last_name=tg_last_name,
        language_code=language_code,
        bot_language=bot_language,
        phone=raw_phone,
        phone_normalized=normalized_phone,
        email=email,
        company=company,
        employee_company=employee_company,
        is_verified=True,
    )

    return RegisterByInnResult(
        profile=profile,
        company=company,
        employee_company=employee_company,
        company_created=company_created,
    )
