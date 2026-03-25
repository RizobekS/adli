from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from apps.tg_bot.bot.utils.i18n import tr, get_i18n_attr


def problem_directions_keyboard(problem_directions, lang: str = "ru") -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text=get_i18n_attr(item, "name", lang),
            callback_data=f"cr:pd:{item.id}"
        )]
        for item in problem_directions
    ]
    rows.append([InlineKeyboardButton(text=tr(lang, "cancel"), callback_data="cr:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def categories_keyboard(categories, lang: str = "ru") -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text=get_i18n_attr(item, "name", lang),
            callback_data=f"cr:cat:{item.id}"
        )]
        for item in categories
    ]
    rows.append([InlineKeyboardButton(text=tr(lang, "cancel"), callback_data="cr:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def directions_keyboard(directions, selected_ids: set[int] | None = None, lang: str = "ru") -> InlineKeyboardMarkup:
    selected_ids = selected_ids or set()
    rows = []

    for item in directions:
        checked = "✅ " if item.id in selected_ids else ""
        rows.append([
            InlineKeyboardButton(
                text=f"{checked}{get_i18n_attr(item, 'title', lang)}",
                callback_data=f"cr:dir:{item.id}",
            )
        ])

    rows.append([InlineKeyboardButton(text=tr(lang, "done"), callback_data="cr:dir:done")])
    rows.append([InlineKeyboardButton(text=tr(lang, "skip"), callback_data="cr:dir:skip")])
    rows.append([InlineKeyboardButton(text=tr(lang, "cancel"), callback_data="cr:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def regions_keyboard(regions, lang: str = "ru") -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text=get_i18n_attr(item, "name", lang),
            callback_data=f"cr:reg:{item.id}"
        )]
        for item in regions
    ]
    rows.append([InlineKeyboardButton(text=tr(lang, "cancel"), callback_data="cr:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def districts_keyboard(districts, lang: str = "ru") -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text=get_i18n_attr(item, "name", lang),
            callback_data=f"cr:dist:{item.id}"
        )]
        for item in districts
    ]
    rows.append([InlineKeyboardButton(text=tr(lang, "back"), callback_data="cr:back:region")])
    rows.append([InlineKeyboardButton(text=tr(lang, "cancel"), callback_data="cr:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def attachment_actions_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=tr(lang, "done"), callback_data="cr:file:done")],
            [InlineKeyboardButton(text=tr(lang, "skip"), callback_data="cr:file:skip")],
            [InlineKeyboardButton(text=tr(lang, "cancel"), callback_data="cr:cancel")],
        ]
    )


def confirm_request_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=tr(lang, "send"), callback_data="cr:confirm")],
            [InlineKeyboardButton(text=tr(lang, "cancel"), callback_data="cr:cancel")],
        ]
    )


def reg_regions_keyboard(regions, allow_skip: bool = False, lang: str = "ru") -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text=get_i18n_attr(item, "name", lang),
            callback_data=f"reg:reg:{item.id}"
        )]
        for item in regions
    ]
    if allow_skip:
        rows.append([InlineKeyboardButton(text=tr(lang, "skip"), callback_data="reg:reg:skip")])
    rows.append([InlineKeyboardButton(text=tr(lang, "cancel"), callback_data="reg:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def reg_districts_keyboard(districts, allow_skip: bool = False, lang: str = "ru") -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text=get_i18n_attr(item, "name", lang),
            callback_data=f"reg:dist:{item.id}"
        )]
        for item in districts
    ]
    rows.append([InlineKeyboardButton(text=tr(lang, "back"), callback_data="reg:back:region")])
    if allow_skip:
        rows.append([InlineKeyboardButton(text=tr(lang, "skip"), callback_data="reg:dist:skip")])
    rows.append([InlineKeyboardButton(text=tr(lang, "cancel"), callback_data="reg:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def reg_categories_keyboard(categories, allow_skip: bool = False, lang: str = "ru") -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text=get_i18n_attr(item, "name", lang),
            callback_data=f"reg:cat:{item.id}"
        )]
        for item in categories
    ]
    if allow_skip:
        rows.append([InlineKeyboardButton(text=tr(lang, "skip"), callback_data="reg:cat:skip")])
    rows.append([InlineKeyboardButton(text=tr(lang, "cancel"), callback_data="reg:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def reg_directions_keyboard(directions, selected_ids: set[int] | None = None, lang: str = "ru") -> InlineKeyboardMarkup:
    selected_ids = selected_ids or set()
    rows = []

    for item in directions:
        checked = "✅ " if item.id in selected_ids else ""
        rows.append([
            InlineKeyboardButton(
                text=f"{checked}{get_i18n_attr(item, 'title', lang)}",
                callback_data=f"reg:dir:{item.id}",
            )
        ])

    rows.append([InlineKeyboardButton(text=tr(lang, "done"), callback_data="reg:dir:done")])
    rows.append([InlineKeyboardButton(text=tr(lang, "skip"), callback_data="reg:dir:skip")])
    rows.append([InlineKeyboardButton(text=tr(lang, "cancel"), callback_data="reg:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def reg_confirm_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=tr(lang, "confirm"), callback_data="reg:confirm")],
            [InlineKeyboardButton(text=tr(lang, "cancel"), callback_data="reg:cancel")],
        ]
    )