from asgiref.sync import sync_to_async
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from apps.tg_bot.selectors import get_user_bot_language
from apps.tg_bot.bot.utils.i18n import tr
from apps.tg_bot.bot.utils.recovery import reset_user_dialog

router = Router()


@router.message(F.text.in_(["🏠 Главное меню", "🏠 Bosh menyu"]))
async def force_main_menu(message: Message, state: FSMContext):
    await reset_user_dialog(message, state, reason_key="session_recovered")


@router.callback_query(F.data.in_(["cr:expired", "reg:expired", "fallback:expired"]))
async def expired_callback_handler(callback: CallbackQuery, state: FSMContext):
    await reset_user_dialog(callback, state, reason_key="session_recovered", use_alert=True)


@router.callback_query()
async def unknown_callback_fallback(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if not current_state:
        try:
            await callback.answer("Действие устарело.", show_alert=False)
        except Exception:
            pass
        return

    await reset_user_dialog(callback, state, reason_key="session_recovered", use_alert=True)


@router.message()
async def unknown_message_fallback(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if not current_state:
        return

    # если пользователь в каком-то FSM и пишет что-то не туда,
    # не молчим, а вытаскиваем его обратно
    await reset_user_dialog(message, state, reason_key="unknown_input_recovered")