import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from django.db.utils import Error as DjangoDbError

from apps.tg_bot.services import prepare_request_notification_payload
from apps.tg_bot.bot.utils.db import database_sync_to_async as sync_to_async

logger = logging.getLogger(__name__)


async def notify_request_created(bot: Bot, request_id: int) -> int:
    try:
        payload = await sync_to_async(prepare_request_notification_payload)(request_id)
    except DjangoDbError:
        logger.exception("Failed to prepare Telegram request notification payload: request_id=%s", request_id)
        return 0

    if not payload:
        return 0

    chat_ids = payload.get("chat_ids") or []
    text = payload.get("text") or ""

    sent_count = 0
    for chat_id in chat_ids:
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                disable_web_page_preview=True,
            )
            sent_count += 1
        except (TelegramBadRequest, TelegramForbiddenError):
            continue

    return sent_count
