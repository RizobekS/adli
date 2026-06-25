import logging

from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from apps.tg_bot.selectors import (
    get_user_bot_language,
    get_verified_telegram_profile_by_user_id,
)
from apps.tg_bot.bot.utils.db import database_sync_to_async as sync_to_async
from apps.tg_bot.bot.keyboards.reply import (
    main_menu_keyboard,
    contact_request_keyboard,
)
from apps.tg_bot.bot.states.request_states import AuthStates
from apps.tg_bot.bot.utils.i18n import tr

logger = logging.getLogger(__name__)
DEFAULT_BOT_LANGUAGE = "uz"


def _is_private_event(event: Message | CallbackQuery) -> bool:
    message = event.message if isinstance(event, CallbackQuery) else event
    return bool(message and message.chat.type == "private")


async def _answer_private_chat_required(event: Message | CallbackQuery, lang: str, text: str) -> None:
    message_text = f"{text}\n\n{tr(lang, 'private_chat_required')}"

    if isinstance(event, CallbackQuery):
        if event.message:
            await event.message.answer(message_text)
        return

    await event.answer(message_text)


async def reset_user_dialog(
    event: Message | CallbackQuery,
    state: FSMContext,
    *,
    reason_key: str = "session_recovered",
    use_alert: bool = False,
):
    user = event.from_user
    user_id = user.id if user else 0

    await state.clear()

    try:
        lang = await sync_to_async(get_user_bot_language)(user_id, default=DEFAULT_BOT_LANGUAGE)
    except Exception:
        logger.exception("Failed to load Telegram bot language during dialog recovery")
        lang = DEFAULT_BOT_LANGUAGE

    try:
        profile = await sync_to_async(get_verified_telegram_profile_by_user_id)(user_id)
    except Exception:
        logger.exception("Failed to load Telegram profile during dialog recovery")
        profile = None

    text = tr(lang, reason_key)

    if isinstance(event, CallbackQuery):
        try:
            await event.answer(
                tr(lang, "callback_expired_alert") if use_alert else tr(lang, "action_recovered_short"),
                show_alert=use_alert,
            )
        except Exception:
            pass

        if profile:
            await event.message.answer(
                text,
                reply_markup=main_menu_keyboard(lang),
            )
        else:
            if not _is_private_event(event):
                await _answer_private_chat_required(event, lang, text)
                return

            await state.set_state(AuthStates.waiting_for_contact)
            await event.message.answer(
                text,
                reply_markup=contact_request_keyboard(lang),
            )
        return

    if profile:
        await event.answer(
            text,
            reply_markup=main_menu_keyboard(lang),
        )
    else:
        if not _is_private_event(event):
            await _answer_private_chat_required(event, lang, text)
            return

        await state.set_state(AuthStates.waiting_for_contact)
        await event.answer(
            text,
            reply_markup=contact_request_keyboard(lang),
        )
