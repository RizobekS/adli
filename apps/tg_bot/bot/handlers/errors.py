import logging

from asgiref.sync import sync_to_async
from aiogram import Router
from aiogram.types import ErrorEvent, Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from apps.tg_bot.bot.utils.recovery import reset_user_dialog

logger = logging.getLogger(__name__)
router = Router()


@router.error()
async def global_error_handler(event: ErrorEvent, state: FSMContext):
    logger.exception("Telegram bot error: %s", event.exception, exc_info=event.exception)

    update = event.update

    message = getattr(update, "message", None)
    callback = getattr(update, "callback_query", None)

    try:
        if message:
            await reset_user_dialog(message, state, reason_key="unexpected_error_recovered")
            return True

        if callback:
            await reset_user_dialog(callback, state, reason_key="unexpected_error_recovered", use_alert=True)
            return True
    except Exception:
        logger.exception("Failed to recover from bot error")

    return True