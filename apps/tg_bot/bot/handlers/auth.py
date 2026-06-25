from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from apps.tg_bot.services import verify_telegram_user_by_phone, set_telegram_profile_email
from apps.tg_bot.selectors import get_user_bot_language
from apps.tg_bot.bot.utils.db import database_sync_to_async as sync_to_async
from apps.tg_bot.bot.keyboards.reply import (
    contact_request_keyboard,
    main_menu_keyboard,
)
from apps.tg_bot.bot.states.request_states import AuthStates, RegistrationStates
from apps.tg_bot.bot.utils.i18n import tr
from apps.tg_bot.bot.utils.phone import normalize_uz_phone

router = Router()


def _normalize_email(value: str) -> str:
    return (value or "").strip().lower()

def _is_valid_uz_phone(raw_phone: str) -> bool:
    normalized = normalize_uz_phone(raw_phone)
    digits = normalized.replace("+", "")
    return normalized.startswith("+998") and len(digits) == 12

async def _process_phone_verification(
    *,
    message: Message,
    state: FSMContext,
    raw_phone: str,
):
    tg_user = message.from_user
    lang = await sync_to_async(get_user_bot_language)(tg_user.id if tg_user else 0)

    if not tg_user:
        await message.answer(tr(lang, "unknown_user"))
        return

    raw_phone = (raw_phone or "").strip()

    if not _is_valid_uz_phone(raw_phone):
        await message.answer(
            tr(lang, "phone_invalid"),
            reply_markup=contact_request_keyboard(lang),
        )
        return

    result = await sync_to_async(verify_telegram_user_by_phone)(
        telegram_user_id=tg_user.id,
        chat_id=message.chat.id,
        raw_phone=raw_phone,
        username=tg_user.username or "",
        first_name=tg_user.first_name or "",
        last_name=tg_user.last_name or "",
        language_code=tg_user.language_code or "",
    )

    if not result.matched:
        await state.update_data(raw_phone=raw_phone)
        await state.set_state(RegistrationStates.waiting_for_inn)
        await message.answer(
            tr(lang, "phone_not_found"),
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    company_name = result.company.name if result.company else "—"

    if result.employee_company:
        parts = [
            result.employee_company.first_name or "",
            result.employee_company.last_name or "",
            result.employee_company.middle_name or "",
        ]
        employee_name = " ".join(p for p in parts if p).strip() or "—"
    else:
        employee_name = "—"

    existing_email = ""

    if getattr(result.profile, "email", ""):
        existing_email = result.profile.email

    if result.employee_company and result.employee_company.email:
        existing_email = result.employee_company.email

    if not existing_email:
        await state.update_data(
            verified_company_name=company_name,
            verified_employee_name=employee_name,
        )
        await state.set_state(AuthStates.waiting_for_email)
        await message.answer(tr(lang, "send_email"))
        return

    await state.clear()
    await message.answer(
        tr(
            lang,
            "phone_verified_success",
            company_name=company_name,
            employee_name=employee_name,
        ),
        reply_markup=main_menu_keyboard(lang),
    )


@router.message(AuthStates.waiting_for_contact, F.contact)
async def handle_contact_verification(message: Message, state: FSMContext):
    tg_user = message.from_user
    contact = message.contact
    lang = await sync_to_async(get_user_bot_language)(tg_user.id if tg_user else 0)

    if not tg_user or not contact:
        await message.answer(
            tr(lang, "contact_data_error"),
            reply_markup=contact_request_keyboard(lang),
        )
        return

    if contact.user_id and contact.user_id != tg_user.id:
        await message.answer(
            tr(lang, "send_own_phone"),
            reply_markup=contact_request_keyboard(lang),
        )
        return

    raw_phone = contact.phone_number or ""
    if not raw_phone:
        await message.answer(
            tr(lang, "phone_not_received"),
            reply_markup=contact_request_keyboard(lang),
        )
        return

    await _process_phone_verification(
        message=message,
        state=state,
        raw_phone=raw_phone,
    )


@router.message(AuthStates.waiting_for_email)
async def handle_email_after_phone_verification(message: Message, state: FSMContext):
    tg_user = message.from_user
    lang = await sync_to_async(get_user_bot_language)(tg_user.id if tg_user else 0)

    email = _normalize_email(message.text or "")

    try:
        validate_email(email)
    except ValidationError:
        await message.answer(tr(lang, "email_invalid"))
        return

    if not tg_user:
        await message.answer(tr(lang, "contact_data_error"))
        return

    await sync_to_async(set_telegram_profile_email)(
        telegram_user_id=tg_user.id,
        email=email,
    )

    data = await state.get_data()
    company_name = data.get("verified_company_name", "—")
    employee_name = data.get("verified_employee_name", "—")

    await state.clear()
    await message.answer(
        tr(
            lang,
            "phone_verified_success",
            company_name=company_name,
            employee_name=employee_name,
        ),
        reply_markup=main_menu_keyboard(lang),
    )


@router.message(AuthStates.waiting_for_contact)
async def handle_manual_phone_during_auth(message: Message, state: FSMContext):
    raw_phone = (message.text or "").strip()

    await _process_phone_verification(
        message=message,
        state=state,
        raw_phone=raw_phone,
    )
