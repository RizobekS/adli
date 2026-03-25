from asgiref.sync import sync_to_async
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from apps.tg_bot.services import verify_telegram_user_by_phone
from apps.tg_bot.selectors import get_user_bot_language
from apps.tg_bot.bot.keyboards.reply import (
    contact_request_keyboard,
    main_menu_keyboard,
    phone_not_found_keyboard,
)
from apps.tg_bot.bot.states.request_states import AuthStates
from apps.tg_bot.bot.utils.i18n import tr

router = Router()


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
        await state.set_state(AuthStates.waiting_for_phone_fallback_action)
        await message.answer(
            tr(lang, "phone_not_found"),
            reply_markup=phone_not_found_keyboard(lang),
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
async def handle_non_contact_during_auth(message: Message):
    lang = await sync_to_async(get_user_bot_language)(message.from_user.id if message.from_user else 0)
    await message.answer(
        tr(lang, "send_phone_using_button"),
        reply_markup=contact_request_keyboard(lang),
    )