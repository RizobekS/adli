from asgiref.sync import sync_to_async
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from apps.tg_bot.selectors import (
    get_verified_telegram_profile_by_user_id,
    get_telegram_profile_by_user_id,
)
from apps.tg_bot.services import set_telegram_profile_bot_language
from apps.tg_bot.bot.keyboards.reply import (
    contact_request_keyboard,
    main_menu_keyboard,
    language_keyboard,
)
from apps.tg_bot.bot.states.request_states import AuthStates
from apps.tg_bot.bot.utils.i18n import tr

router = Router()


async def _show_after_language_change(message: Message, state: FSMContext, lang: str):
    tg_user = message.from_user
    verified_profile = await sync_to_async(get_verified_telegram_profile_by_user_id)(tg_user.id)

    if verified_profile:
        company_name = verified_profile.company.name if verified_profile.company else "—"

        if verified_profile.employee_company:
            parts = [
                verified_profile.employee_company.first_name or "",
                verified_profile.employee_company.last_name or "",
                verified_profile.employee_company.middle_name or "",
            ]
            employee_name = " ".join(p for p in parts if p).strip() or "—"
        else:
            employee_name = "—"

        await state.clear()
        await message.answer(
            tr(lang, "language_saved"),
            reply_markup=main_menu_keyboard(lang),
        )
        await message.answer(
            tr(
                lang,
                "start_verified",
                company_name=company_name,
                employee_name=employee_name,
            ),
            reply_markup=main_menu_keyboard(lang),
        )
        return

    await state.set_state(AuthStates.waiting_for_contact)
    await message.answer(
        f"{tr(lang, 'language_saved')}\n\n{tr(lang, 'start_unverified')}",
        reply_markup=contact_request_keyboard(lang),
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    tg_user = message.from_user
    if not tg_user:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    profile = await sync_to_async(get_telegram_profile_by_user_id)(tg_user.id)

    if not profile:
        await state.set_state(AuthStates.choosing_language)
        await message.answer(
            tr("ru", "choose_language"),
            reply_markup=language_keyboard(),
        )
        return

    lang = profile.bot_language or "ru"
    verified_profile = await sync_to_async(get_verified_telegram_profile_by_user_id)(tg_user.id)

    if verified_profile:
        company_name = verified_profile.company.name if verified_profile.company else "—"

        if verified_profile.employee_company:
            parts = [
                verified_profile.employee_company.first_name or "",
                verified_profile.employee_company.last_name or "",
                verified_profile.employee_company.middle_name or "",
            ]
            employee_name = " ".join(p for p in parts if p).strip() or "—"
        else:
            employee_name = "—"

        text = tr(
            lang,
            "start_verified",
            company_name=company_name,
            employee_name=employee_name,
        )
        await message.answer(text, reply_markup=main_menu_keyboard(lang))
        return

    text = tr(lang, "start_unverified")
    await state.set_state(AuthStates.waiting_for_contact)
    await message.answer(text, reply_markup=contact_request_keyboard(lang))


@router.message(F.text.in_(["🌐 Изменить язык", "🌐 Tilni o‘zgartirish"]))
async def open_language_menu(message: Message, state: FSMContext):
    await state.set_state(AuthStates.choosing_language)
    current_lang = "ru"
    if message.from_user:
        profile = await sync_to_async(get_telegram_profile_by_user_id)(message.from_user.id)
        if profile and profile.bot_language:
            current_lang = profile.bot_language

    await message.answer(
        tr(current_lang, "language_menu_hint"),
        reply_markup=language_keyboard(),
    )


@router.message(AuthStates.choosing_language, F.text.in_(["🇷🇺 Русский", "🇺🇿 O‘zbekcha"]))
async def choose_language_handler(message: Message, state: FSMContext):
    tg_user = message.from_user
    if not tg_user:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    lang = "uz" if message.text == "🇺🇿 O‘zbekcha" else "ru"

    await sync_to_async(set_telegram_profile_bot_language)(
        telegram_user_id=tg_user.id,
        chat_id=message.chat.id,
        bot_language=lang,
        username=tg_user.username or "",
        first_name=tg_user.first_name or "",
        last_name=tg_user.last_name or "",
        language_code=tg_user.language_code or "",
    )

    await _show_after_language_change(message, state, lang)