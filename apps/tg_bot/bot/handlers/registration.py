from asgiref.sync import sync_to_async
from django.utils import timezone
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from apps.tg_bot.bot.keyboards.reply import (
    contact_request_keyboard,
    main_menu_keyboard,
    phone_not_found_keyboard,
)
from apps.tg_bot.bot.keyboards.inline import (
    reg_regions_keyboard,
    reg_districts_keyboard,
    reg_categories_keyboard,
    reg_directions_keyboard,
    reg_confirm_keyboard,
)
from apps.tg_bot.bot.states.request_states import AuthStates, RegistrationStates
from apps.tg_bot.bot.utils.i18n import tr, get_i18n_attr
from apps.tg_bot.bot.utils.session_guard import is_session_expired
from apps.tg_bot.bot.utils.recovery import reset_user_dialog
from apps.tg_bot.selectors import (
    find_company_by_inn,
    get_company_direction_ids,
    get_regions,
    get_region_by_id,
    get_districts_by_region,
    get_district_by_id,
    get_categories,
    get_category_by_id,
    get_directions_by_category,
    get_directions_by_ids,
    get_user_bot_language,
)
from apps.tg_bot.services import register_or_bind_telegram_profile_by_inn

router = Router()


async def _registration_preview(state: FSMContext, lang: str = "ru") -> str:
    data = await state.get_data()

    direction_names = []
    if data.get("direction_ids"):
        dirs = await sync_to_async(list)(get_directions_by_ids(data["direction_ids"]))
        direction_names = [get_i18n_attr(x, "title", lang) for x in dirs]

    return tr(
        lang,
        "registration_preview",
        inn=data.get("inn", "—"),
        company_name=data.get("company_name", "—"),
        fio=data.get("fio", "—"),
        region_name=data.get("region_name", "—"),
        district_name=data.get("district_name", "—"),
        category_name=data.get("category_name", "—"),
        direction_names=", ".join(direction_names) if direction_names else "—",
    )


@router.message(
    AuthStates.waiting_for_phone_fallback_action,
    F.text.in_(["🔎 Указать ИНН", "🔎 STIRni kiritish"]),
)
async def start_registration_by_inn(message: Message, state: FSMContext):
    lang = await sync_to_async(get_user_bot_language)(message.from_user.id if message.from_user else 0)

    await state.set_state(RegistrationStates.waiting_for_inn)
    await state.update_data(last_step_at=timezone.now().isoformat())

    await message.answer(
        tr(lang, "enter_company_inn"),
        reply_markup=phone_not_found_keyboard(lang),
    )


@router.message(AuthStates.waiting_for_phone_fallback_action, F.contact)
async def retry_phone_from_fallback(message: Message, state: FSMContext):
    lang = await sync_to_async(get_user_bot_language)(message.from_user.id if message.from_user else 0)
    await state.set_state(AuthStates.waiting_for_contact)
    await message.answer(
        tr(lang, "send_phone_below"),
        reply_markup=contact_request_keyboard(lang),
    )


@router.message(
    AuthStates.waiting_for_phone_fallback_action,
    F.text.in_(["❌ Отмена", "❌ Bekor qilish"]),
)
async def cancel_fallback(message: Message, state: FSMContext):
    lang = await sync_to_async(get_user_bot_language)(message.from_user.id if message.from_user else 0)
    await state.clear()
    await message.answer(
        tr(lang, "action_cancelled"),
        reply_markup=contact_request_keyboard(lang),
    )


@router.message(RegistrationStates.waiting_for_inn)
async def input_inn(message: Message, state: FSMContext):
    data = await state.get_data()
    if is_session_expired(data):
        await reset_user_dialog(message, state, reason_key="session_recovered")
        return

    lang = await sync_to_async(get_user_bot_language)(message.from_user.id if message.from_user else 0)
    inn = "".join(ch for ch in (message.text or "") if ch.isdigit())

    if len(inn) < 9:
        await message.answer(tr(lang, "inn_too_short"))
        return

    company = await sync_to_async(find_company_by_inn)(inn)
    await state.update_data(
        inn=inn,
        last_step_at=timezone.now().isoformat(),
    )

    if company:
        direction_ids = await sync_to_async(get_company_direction_ids)(company.id)

        await state.update_data(
            company_exists=True,
            company_id=company.id,
            company_name=company.name,
            region_id=company.region_id if company.region_id else None,
            region_name=get_i18n_attr(company.region, "name", lang) if getattr(company, "region", None) else None,
            district_id=company.district_id if company.district_id else None,
            district_name=get_i18n_attr(company.district, "name", lang) if getattr(company, "district", None) else None,
            category_id=company.category_id if company.category_id else None,
            category_name=get_i18n_attr(company.category, "name", lang) if getattr(company, "category", None) else None,
            direction_ids=direction_ids,
            last_step_at=timezone.now().isoformat(),
        )

        regions = await sync_to_async(list)(get_regions())
        await state.set_state(RegistrationStates.choosing_region)
        await message.answer(
            tr(lang, "company_found", company_name=company.name),
            reply_markup=reg_regions_keyboard(regions, allow_skip=True, lang=lang),
        )
        return

    await state.update_data(
        company_exists=False,
        region_id=None,
        region_name=None,
        district_id=None,
        district_name=None,
        category_id=None,
        category_name=None,
        direction_ids=[],
        last_step_at=timezone.now().isoformat(),
    )
    await state.set_state(RegistrationStates.waiting_for_company_name)
    await message.answer(tr(lang, "company_not_found_enter_name"))


@router.message(RegistrationStates.waiting_for_company_name)
async def input_company_name(message: Message, state: FSMContext):
    data = await state.get_data()
    if is_session_expired(data):
        await reset_user_dialog(message, state, reason_key="session_recovered")
        return

    lang = await sync_to_async(get_user_bot_language)(message.from_user.id if message.from_user else 0)
    company_name = (message.text or "").strip()

    if len(company_name) < 3:
        await message.answer(tr(lang, "company_name_too_short"))
        return

    await state.update_data(
        company_name=company_name,
        last_step_at=timezone.now().isoformat(),
    )

    regions = await sync_to_async(list)(get_regions())
    await state.set_state(RegistrationStates.choosing_region)
    await message.answer(
        tr(lang, "choose_company_region"),
        reply_markup=reg_regions_keyboard(regions, allow_skip=False, lang=lang),
    )


@router.callback_query(RegistrationStates.choosing_region, F.data.startswith("reg:reg:"))
async def choose_reg_region(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if is_session_expired(data):
        await reset_user_dialog(callback, state, reason_key="session_recovered", use_alert=True)
        return

    lang = await sync_to_async(get_user_bot_language)(callback.from_user.id if callback.from_user else 0)
    token = callback.data.split(":")[-1]

    if token == "skip":
        await state.set_state(RegistrationStates.waiting_for_fio)
        await state.update_data(last_step_at=timezone.now().isoformat())
        await callback.message.edit_text(tr(lang, "send_fio"))
        await callback.answer()
        return

    region_id = int(token)
    region = await sync_to_async(get_region_by_id)(region_id)

    if not region:
        await callback.answer(tr(lang, "region_not_found"), show_alert=True)
        return

    allow_skip = bool(data.get("company_exists"))

    await state.update_data(
        region_id=region.id,
        region_name=get_i18n_attr(region, "name", lang),
        district_id=None,
        district_name=None,
        last_step_at=timezone.now().isoformat(),
    )
    districts = await sync_to_async(list)(get_districts_by_region(region.id))
    await state.set_state(RegistrationStates.choosing_district)
    await callback.message.edit_text(
        tr(lang, "choose_company_district"),
        reply_markup=reg_districts_keyboard(districts, allow_skip=allow_skip, lang=lang),
    )
    await callback.answer()


@router.callback_query(RegistrationStates.choosing_district, F.data == "reg:back:region")
async def reg_back_to_region(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if is_session_expired(data):
        await reset_user_dialog(callback, state, reason_key="session_recovered", use_alert=True)
        return

    lang = await sync_to_async(get_user_bot_language)(callback.from_user.id if callback.from_user else 0)
    allow_skip = bool(data.get("company_exists"))

    regions = await sync_to_async(list)(get_regions())
    await state.set_state(RegistrationStates.choosing_region)
    await state.update_data(last_step_at=timezone.now().isoformat())
    await callback.message.edit_text(
        tr(lang, "choose_company_region"),
        reply_markup=reg_regions_keyboard(regions, allow_skip=allow_skip, lang=lang),
    )
    await callback.answer()


@router.callback_query(RegistrationStates.choosing_district, F.data.startswith("reg:dist:"))
async def choose_reg_district(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if is_session_expired(data):
        await reset_user_dialog(callback, state, reason_key="session_recovered", use_alert=True)
        return

    lang = await sync_to_async(get_user_bot_language)(callback.from_user.id if callback.from_user else 0)
    token = callback.data.split(":")[-1]

    if token == "skip":
        await state.set_state(RegistrationStates.waiting_for_fio)
        await state.update_data(last_step_at=timezone.now().isoformat())
        await callback.message.edit_text(tr(lang, "send_fio"))
        await callback.answer()
        return

    district_id = int(token)
    district = await sync_to_async(get_district_by_id)(district_id)

    if not district:
        await callback.answer(tr(lang, "district_not_found"), show_alert=True)
        return

    await state.update_data(
        district_id=district.id,
        district_name=get_i18n_attr(district, "name", lang),
        last_step_at=timezone.now().isoformat(),
    )
    await state.set_state(RegistrationStates.waiting_for_fio)
    await callback.message.edit_text(tr(lang, "send_fio"))
    await callback.answer()


@router.message(RegistrationStates.waiting_for_fio)
async def input_fio(message: Message, state: FSMContext):
    data = await state.get_data()
    if is_session_expired(data):
        await reset_user_dialog(message, state, reason_key="session_recovered")
        return

    lang = await sync_to_async(get_user_bot_language)(message.from_user.id if message.from_user else 0)
    fio = " ".join((message.text or "").strip().split())

    if len(fio) < 5:
        await message.answer(tr(lang, "fio_too_short"))
        return

    allow_skip = bool(data.get("company_exists"))

    await state.update_data(
        fio=fio,
        last_step_at=timezone.now().isoformat(),
    )
    categories = await sync_to_async(list)(get_categories())
    await state.set_state(RegistrationStates.choosing_category)
    await message.answer(
        tr(lang, "choose_category"),
        reply_markup=reg_categories_keyboard(categories, allow_skip=allow_skip, lang=lang),
    )


@router.callback_query(RegistrationStates.choosing_category, F.data.startswith("reg:cat:"))
async def choose_reg_category(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if is_session_expired(data):
        await reset_user_dialog(callback, state, reason_key="session_recovered", use_alert=True)
        return

    lang = await sync_to_async(get_user_bot_language)(callback.from_user.id if callback.from_user else 0)
    token = callback.data.split(":")[-1]

    if token == "skip":
        existing_category_id = data.get("category_id")
        if existing_category_id:
            directions = await sync_to_async(list)(get_directions_by_category(existing_category_id))
        else:
            directions = []

        await state.set_state(RegistrationStates.choosing_directions)
        await state.update_data(last_step_at=timezone.now().isoformat())
        await callback.message.edit_text(
            tr(lang, "choose_directions"),
            reply_markup=reg_directions_keyboard(
                directions,
                selected_ids=set(data.get("direction_ids", [])),
                lang=lang,
            ),
        )
        await callback.answer()
        return

    category_id = int(token)
    category = await sync_to_async(get_category_by_id)(category_id)

    if not category:
        await callback.answer(tr(lang, "category_not_found"), show_alert=True)
        return

    await state.update_data(
        category_id=category.id,
        category_name=get_i18n_attr(category, "name", lang),
        direction_ids=[],
        last_step_at=timezone.now().isoformat(),
    )

    directions = await sync_to_async(list)(get_directions_by_category(category.id))
    await state.set_state(RegistrationStates.choosing_directions)
    await callback.message.edit_text(
        tr(lang, "choose_directions"),
        reply_markup=reg_directions_keyboard(directions, selected_ids=set(), lang=lang),
    )
    await callback.answer()


@router.callback_query(RegistrationStates.choosing_directions, F.data.startswith("reg:dir:"))
async def choose_reg_directions(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if is_session_expired(data):
        await reset_user_dialog(callback, state, reason_key="session_recovered", use_alert=True)
        return

    lang = await sync_to_async(get_user_bot_language)(callback.from_user.id if callback.from_user else 0)
    token = callback.data.split(":")[-1]
    selected_ids = set(data.get("direction_ids", []))
    category_id = data.get("category_id")

    if token == "done":
        preview = await _registration_preview(state, lang)
        await state.set_state(RegistrationStates.confirming)
        await state.update_data(last_step_at=timezone.now().isoformat())
        await callback.message.edit_text(preview, reply_markup=reg_confirm_keyboard(lang))
        await callback.answer()
        return

    if token == "skip":
        preview = await _registration_preview(state, lang)
        await state.set_state(RegistrationStates.confirming)
        await state.update_data(last_step_at=timezone.now().isoformat())
        await callback.message.edit_text(preview, reply_markup=reg_confirm_keyboard(lang))
        await callback.answer()
        return

    direction_id = int(token)
    if direction_id in selected_ids:
        selected_ids.remove(direction_id)
    else:
        selected_ids.add(direction_id)

    await state.update_data(
        direction_ids=list(selected_ids),
        last_step_at=timezone.now().isoformat(),
    )

    directions = []
    if category_id:
        directions = await sync_to_async(list)(get_directions_by_category(category_id))

    await callback.message.edit_reply_markup(
        reply_markup=reg_directions_keyboard(directions, selected_ids=selected_ids, lang=lang)
    )
    await callback.answer(tr(lang, "updated_list"))


@router.callback_query(F.data == "reg:cancel")
async def cancel_registration(callback: CallbackQuery, state: FSMContext):
    lang = await sync_to_async(get_user_bot_language)(callback.from_user.id if callback.from_user else 0)
    await state.clear()
    await callback.message.answer(
        tr(lang, "registration_cancelled"),
        reply_markup=contact_request_keyboard(lang),
    )
    await callback.answer()


@router.callback_query(RegistrationStates.confirming, F.data == "reg:confirm")
async def confirm_registration(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if is_session_expired(data):
        await reset_user_dialog(callback, state, reason_key="session_recovered", use_alert=True)
        return

    lang = await sync_to_async(get_user_bot_language)(callback.from_user.id if callback.from_user else 0)
    tg_user = callback.from_user

    region = await sync_to_async(get_region_by_id)(data["region_id"]) if data.get("region_id") else None
    district = await sync_to_async(get_district_by_id)(data["district_id"]) if data.get("district_id") else None
    category = await sync_to_async(get_category_by_id)(data["category_id"]) if data.get("category_id") else None
    directions = await sync_to_async(list)(get_directions_by_ids(data.get("direction_ids", []))) if data.get("direction_ids") else []

    result = await sync_to_async(register_or_bind_telegram_profile_by_inn)(
        telegram_user_id=tg_user.id,
        chat_id=callback.message.chat.id,
        raw_phone=data.get("raw_phone", ""),
        username=tg_user.username or "",
        tg_first_name=tg_user.first_name or "",
        tg_last_name=tg_user.last_name or "",
        language_code=tg_user.language_code or "",
        inn=data["inn"],
        company_name=data.get("company_name", ""),
        fio=data.get("fio", ""),
        region=region,
        district=district,
        category=category,
        directions=directions,
    )

    await state.clear()

    action_text = tr(
        lang,
        "company_registered_new" if result.company_created else "company_registered_bound"
    )

    await callback.message.answer(
        tr(
            lang,
            "company_registered_success",
            action_text=action_text,
            company_name=result.company.name,
            inn=result.company.inn,
        ),
        reply_markup=main_menu_keyboard(lang),
    )
    await callback.answer()