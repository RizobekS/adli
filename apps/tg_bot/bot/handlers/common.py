from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from asgiref.sync import sync_to_async

from apps.tg_bot.selectors import (
    get_verified_telegram_profile_by_user_id,
    get_recent_requests_for_profile,
    get_user_bot_language,
)
from apps.tg_bot.services import bind_group_chat, format_request_short_text
from apps.tg_bot.bot.keyboards.reply import main_menu_keyboard
from apps.tg_bot.bot.utils.i18n import tr

router = Router()


@router.message(F.text.in_(["ℹ️ Помощь", "ℹ️ Yordam"]))
async def help_handler(message: Message):
    lang = await sync_to_async(get_user_bot_language)(message.from_user.id if message.from_user else 0)
    await message.answer(
        tr(lang, "help_text"),
        reply_markup=main_menu_keyboard(lang),
    )


@router.message(F.text.in_(["📄 Мои обращения", "📄 Mening murojaatlarim"]))
async def my_requests_handler(message: Message):
    lang = await sync_to_async(get_user_bot_language)(message.from_user.id if message.from_user else 0)

    profile = await sync_to_async(get_verified_telegram_profile_by_user_id)(message.from_user.id)
    if not profile:
        await message.answer(tr(lang, "verify_first"))
        return

    requests_list = await sync_to_async(list)(get_recent_requests_for_profile(profile, limit=10))
    if not requests_list:
        await message.answer(
            tr(lang, "no_requests"),
            reply_markup=main_menu_keyboard(lang),
        )
        return

    chunks = [tr(lang, "my_recent_requests")]
    for item in requests_list:
        chunks.append(format_request_short_text(item, lang=lang))
        chunks.append("")

    await message.answer(
        "\n".join(chunks).strip(),
        reply_markup=main_menu_keyboard(lang),
    )


@router.message(Command("bind_group"))
async def bind_group_handler(message: Message):
    lang = await sync_to_async(get_user_bot_language)(message.from_user.id if message.from_user else 0)

    if message.chat.type not in ("group", "supergroup"):
        await message.answer(tr(lang, "bind_group_only"))
        return

    await sync_to_async(bind_group_chat)(
        chat_id=message.chat.id,
        title=message.chat.title or "",
        chat_type=message.chat.type,
        department=None,
        is_active=True,
    )

    await message.answer(tr(lang, "group_bound"))