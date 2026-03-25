from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from apps.tg_bot.bot.utils.i18n import tr


def language_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇷🇺 Русский")],
            [KeyboardButton(text="🇺🇿 O‘zbekcha")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def contact_request_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=tr(lang, "send_contact"), request_contact=True)],
            [KeyboardButton(text=tr(lang, "change_language"))],
            [KeyboardButton(text=tr(lang, "main_menu"))],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def phone_not_found_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=tr(lang, "specify_inn"))],
            [KeyboardButton(text=tr(lang, "send_other_phone"), request_contact=True)],
            [KeyboardButton(text=tr(lang, "change_language"))],
            [KeyboardButton(text=tr(lang, "main_menu"))],
            [KeyboardButton(text=tr(lang, "cancel"))],
        ],
        resize_keyboard=True,
    )


def main_menu_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=tr(lang, "create_request"))],
            [KeyboardButton(text=tr(lang, "my_requests"))],
            [KeyboardButton(text=tr(lang, "help"))],
            [KeyboardButton(text=tr(lang, "change_language"))],
            [KeyboardButton(text=tr(lang, "main_menu"))],
        ],
        resize_keyboard=True,
    )