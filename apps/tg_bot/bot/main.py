import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from django.conf import settings

from apps.tg_bot.bot.handlers import start, auth, common, create_request, registration, recovery, errors

logger = logging.getLogger(__name__)


def build_bot() -> Bot:
    if not settings.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

    return Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=settings.TELEGRAM_BOT_PARSE_MODE),
    )


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher()

    dp.include_router(start.router)
    dp.include_router(auth.router)
    dp.include_router(registration.router)
    dp.include_router(common.router)
    dp.include_router(create_request.router)
    dp.include_router(recovery.router)
    dp.include_router(errors.router)

    return dp


async def _run_polling():
    bot = build_bot()
    dp = build_dispatcher()

    logger.info("Starting Telegram bot polling...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


def run_polling():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    asyncio.run(_run_polling())