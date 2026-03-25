from __future__ import annotations

from typing import Optional

from apps.agency.models import ProblemDirection, Department
from apps.companies.models import (
    Company,
    EmployeeCompany,
    Region,
    District,
    Category,
    Direction,
    CompanyPhone,
)
from apps.requests.models import Request
from .models import TelegramProfile, TelegramChatBinding
from .bot.utils.phone import phone_candidates


def get_telegram_profile_by_user_id(telegram_user_id: int) -> Optional[TelegramProfile]:
    return (
        TelegramProfile.objects
        .select_related(
            "company",
            "employee_company",
            "employee_company__company",
            "employee_company__position",
        )
        .filter(telegram_user_id=telegram_user_id)
        .first()
    )


def get_user_bot_language(user_id: int, default: str = "ru") -> str:
    profile = TelegramProfile.objects.filter(telegram_user_id=user_id).only("bot_language").first()
    if profile and profile.bot_language:
        return profile.bot_language
    return default


def get_verified_telegram_profile_by_user_id(telegram_user_id: int) -> Optional[TelegramProfile]:
    return (
        TelegramProfile.objects
        .select_related(
            "company",
            "employee_company",
            "employee_company__company",
            "employee_company__position",
        )
        .filter(telegram_user_id=telegram_user_id, is_verified=True, is_active=True)
        .first()
    )


def find_employee_company_by_phone(raw_phone: str) -> Optional[EmployeeCompany]:
    candidates = phone_candidates(raw_phone)
    if not candidates:
        return None

    return (
        EmployeeCompany.objects
        .select_related("company", "position")
        .filter(phone__in=candidates)
        .order_by("id")
        .first()
    )


def find_company_by_phone(raw_phone: str) -> Optional[Company]:
    candidates = phone_candidates(raw_phone)
    if not candidates:
        return None

    company_phone = (
        CompanyPhone.objects
        .select_related("company")
        .filter(phone__in=candidates)
        .order_by("id")
        .first()
    )
    if company_phone:
        return company_phone.company

    employee = find_employee_company_by_phone(raw_phone)
    if employee:
        return employee.company

    return None


def get_problem_directions():
    return ProblemDirection.objects.select_related("department").order_by("name")


def get_categories():
    return Category.objects.order_by("name")


def get_company_direction_ids(company_id: int) -> list[int]:
    company = (
        Company.objects
        .prefetch_related("directions")
        .filter(id=company_id)
        .first()
    )
    if not company:
        return []
    return list(company.directions.values_list("id", flat=True))


def get_company_request_context(company_id: int) -> dict | None:
    company = (
        Company.objects
        .select_related("category", "region", "district")
        .prefetch_related("directions")
        .filter(id=company_id)
        .first()
    )
    if not company:
        return None

    return {
        "company": company,
        "category": company.category,
        "region": company.region,
        "district": company.district,
        "directions": list(company.directions.all()),
    }


def get_directions():
    return Direction.objects.order_by("title")


def get_directions_by_category(category_id: int):
    return (
        Direction.objects
        .filter(category_id=category_id)
        .order_by("title")
    )


def get_regions():
    return Region.objects.order_by("name")


def get_districts_by_region(region_id: int):
    return District.objects.filter(region_id=region_id).select_related("region").order_by("name")


def get_active_notification_chats_for_department(department: Department | None):
    qs = TelegramChatBinding.objects.filter(is_active=True)

    if department is None:
        return qs.filter(department__isnull=True).order_by("id")

    return qs.filter(department=department).order_by("id")


def get_request_detail_for_notification(request_id: int) -> Optional[Request]:
    return (
        Request.objects
        .select_related(
            "company",
            "employee",
            "problem_direction",
            "assigned_department",
            "assigned_employee",
        )
        .prefetch_related("directions")
        .filter(id=request_id)
        .first()
    )

def get_problem_direction_by_id(problem_direction_id: int):
    return (
        ProblemDirection.objects
        .select_related("department")
        .filter(id=problem_direction_id)
        .first()
    )


def get_category_by_id(category_id: int):
    return Category.objects.filter(id=category_id).first()


def get_directions_by_ids(direction_ids: list[int]):
    return Direction.objects.filter(id__in=direction_ids).order_by("title")


def get_region_by_id(region_id: int):
    return Region.objects.filter(id=region_id).first()


def get_district_by_id(district_id: int):
    return District.objects.select_related("region").filter(id=district_id).first()


def get_recent_requests_for_profile(profile: TelegramProfile, limit: int = 10):
    qs = (
        Request.objects
        .select_related("company", "employee", "problem_direction", "assigned_department")
        .prefetch_related("files")
        .order_by("-created_at")
    )

    if profile.employee_company_id:
        return qs.filter(employee=profile.employee_company)[:limit]

    if profile.company_id:
        return qs.filter(company=profile.company)[:limit]

    return qs.none()


def find_company_by_inn(inn: str) -> Optional[Company]:
    inn = (inn or "").strip()
    if not inn:
        return None
    return (
        Company.objects
        .select_related("region", "district", "category")
        .filter(inn=inn)
        .first()
    )


def find_employee_company_by_company_and_phone(company: Company, raw_phone: str) -> Optional[EmployeeCompany]:
    candidates = phone_candidates(raw_phone)
    if not candidates:
        return None

    return (
        EmployeeCompany.objects
        .select_related("company", "position")
        .filter(company=company, phone__in=candidates)
        .order_by("id")
        .first()
    )