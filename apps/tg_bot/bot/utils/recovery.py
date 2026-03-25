from asgiref.sync import sync_to_async
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from apps.tg_bot.selectors import (
    get_user_bot_language,
    get_verified_telegram_profile_by_user_id,
)
from apps.tg_bot.bot.keyboards.reply import (
    main_menu_keyboard,
    contact_request_keyboard,
)
from apps.tg_bot.bot.states.request_states import AuthStates
from apps.tg_bot.bot.utils.i18n import tr


async def reset_user_dialog(
    event: Message | CallbackQuery,
    state: FSMContext,
    *,
    reason_key: str = "session_recovered",
    use_alert: bool = False,
):
    user = event.from_user
    user_id = user.id if user else 0
    lang = await sync_to_async(get_user_bot_language)(user_id)

    await state.clear()

    profile = await sync_to_async(get_verified_telegram_profile_by_user_id)(user_id)

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
        await state.set_state(AuthStates.waiting_for_contact)
        await event.answer(
            text,
            reply_markup=contact_request_keyboard(lang),
        )