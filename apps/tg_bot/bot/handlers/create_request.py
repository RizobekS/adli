from asgiref.sync import sync_to_async
from django.utils import timezone
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from apps.tg_bot.bot.keyboards.reply import main_menu_keyboard
from apps.tg_bot.bot.keyboards.inline import (
    problem_directions_keyboard,
    attachment_actions_keyboard,
    confirm_request_keyboard,
)
from apps.tg_bot.bot.states.request_states import RequestCreateStates
from apps.tg_bot.bot.utils.files import (
    MAX_ATTACH_BYTES,
    is_allowed_filename,
    build_safe_photo_name,
    download_telegram_attachments,
)
from apps.tg_bot.bot.utils.notifications import notify_request_created
from apps.tg_bot.bot.utils.i18n import tr, get_i18n_attr, translate_request_status
from apps.tg_bot.bot.utils.session_guard import is_session_expired
from apps.tg_bot.bot.utils.recovery import reset_user_dialog
from apps.tg_bot.selectors import (
    get_verified_telegram_profile_by_user_id,
    get_problem_directions,
    get_problem_direction_by_id,
    get_user_bot_language,
    get_company_request_context,
)
from apps.tg_bot.services import create_request_from_telegram_profile

router = Router()


async def _require_verified_profile(message_or_callback):
    tg_user = message_or_callback.from_user
    return await sync_to_async(get_verified_telegram_profile_by_user_id)(tg_user.id)


async def _build_preview_text(state: FSMContext, lang: str) -> str:
    data = await state.get_data()
    attachments_meta = data.get("attachments_meta", [])
    files_count = len(attachments_meta)

    return tr(
        lang,
        "request_preview_short",
        problem_direction_name=data.get("problem_direction_name", "—"),
        files_count=files_count,
        description=data.get("description", ""),
    )


@router.message(F.text.in_(["➕ Создать обращение", "➕ Murojaat yaratish"]))
async def create_request_entry_handler(message: Message, state: FSMContext):
    lang = await sync_to_async(get_user_bot_language)(message.from_user.id if message.from_user else 0)
    profile = await _require_verified_profile(message)

    if not profile:
        await message.answer(tr(lang, "verify_first"))
        return

    await state.clear()

    items = await sync_to_async(list)(get_problem_directions())
    if not items:
        await message.answer(
            tr(lang, "problem_directions_not_configured"),
            reply_markup=main_menu_keyboard(lang),
        )
        return

    await state.set_state(RequestCreateStates.choosing_problem_direction)
    await state.update_data(last_step_at=timezone.now().isoformat())

    await message.answer(
        tr(lang, "request_step_1_short"),
        reply_markup=problem_directions_keyboard(items, lang),
    )


@router.callback_query(F.data == "cr:cancel")
async def cancel_create_request(callback: CallbackQuery, state: FSMContext):
    lang = await sync_to_async(get_user_bot_language)(callback.from_user.id if callback.from_user else 0)
    await state.clear()
    await callback.message.answer(
        tr(lang, "request_cancelled"),
        reply_markup=main_menu_keyboard(lang),
    )
    await callback.answer()


@router.callback_query(RequestCreateStates.choosing_problem_direction, F.data.startswith("cr:pd:"))
async def choose_problem_direction(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if is_session_expired(data):
        await reset_user_dialog(callback, state, reason_key="session_recovered", use_alert=True)
        return

    lang = await sync_to_async(get_user_bot_language)(callback.from_user.id if callback.from_user else 0)
    item_id = int(callback.data.split(":")[-1])
    item = await sync_to_async(get_problem_direction_by_id)(item_id)

    if not item:
        await callback.answer(tr(lang, "problem_direction_not_found"), show_alert=True)
        return

    await state.update_data(
        problem_direction_id=item.id,
        problem_direction_name=get_i18n_attr(item, "name", lang),
        last_step_at=timezone.now().isoformat(),
    )

    await state.set_state(RequestCreateStates.typing_description)
    await callback.message.edit_text(tr(lang, "request_step_2_short"))
    await callback.answer()


@router.message(RequestCreateStates.typing_description)
async def input_description(message: Message, state: FSMContext):
    data = await state.get_data()
    if is_session_expired(data):
        await reset_user_dialog(message, state, reason_key="session_recovered")
        return

    lang = await sync_to_async(get_user_bot_language)(message.from_user.id if message.from_user else 0)
    text = (message.text or "").strip()

    if len(text) < 10:
        await message.answer(tr(lang, "request_description_too_short"))
        return

    await state.update_data(
        description=text,
        attachments_meta=[],
        last_step_at=timezone.now().isoformat(),
    )
    await state.set_state(RequestCreateStates.uploading_files)
    await message.answer(
        tr(lang, "request_step_3_short"),
        reply_markup=attachment_actions_keyboard(lang),
    )


@router.message(RequestCreateStates.uploading_files, F.document)
async def upload_document(message: Message, state: FSMContext):
    data = await state.get_data()
    if is_session_expired(data):
        await reset_user_dialog(message, state, reason_key="session_recovered")
        return

    lang = await sync_to_async(get_user_bot_language)(message.from_user.id if message.from_user else 0)
    doc = message.document
    filename = doc.file_name or "document"
    file_size = doc.file_size or 0

    if file_size > MAX_ATTACH_BYTES:
        await message.answer(tr(lang, "file_too_large"))
        return

    if not is_allowed_filename(filename):
        await message.answer(tr(lang, "invalid_file_type"))
        return

    attachments_meta = data.get("attachments_meta", [])
    attachments_meta.append({
        "file_id": doc.file_id,
        "filename": filename,
        "kind": "document",
    })
    await state.update_data(
        attachments_meta=attachments_meta,
        last_step_at=timezone.now().isoformat(),
    )

    await message.answer(
        tr(lang, "file_added", filename=filename, count=len(attachments_meta)),
        reply_markup=attachment_actions_keyboard(lang),
    )


@router.message(RequestCreateStates.uploading_files, F.photo)
async def upload_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    if is_session_expired(data):
        await reset_user_dialog(message, state, reason_key="session_recovered")
        return

    lang = await sync_to_async(get_user_bot_language)(message.from_user.id if message.from_user else 0)
    photo = message.photo[-1]
    file_size = photo.file_size or 0

    if file_size > MAX_ATTACH_BYTES:
        await message.answer(tr(lang, "photo_too_large"))
        return

    filename = build_safe_photo_name(photo.file_unique_id, fallback=photo.file_id)

    attachments_meta = data.get("attachments_meta", [])
    attachments_meta.append({
        "file_id": photo.file_id,
        "filename": filename,
        "kind": "photo",
    })
    await state.update_data(
        attachments_meta=attachments_meta,
        last_step_at=timezone.now().isoformat(),
    )

    await message.answer(
        tr(lang, "photo_added", count=len(attachments_meta)),
        reply_markup=attachment_actions_keyboard(lang),
    )


@router.message(RequestCreateStates.uploading_files)
async def upload_files_fallback(message: Message):
    lang = await sync_to_async(get_user_bot_language)(message.from_user.id if message.from_user else 0)
    await message.answer(
        tr(lang, "upload_file_hint"),
        reply_markup=attachment_actions_keyboard(lang),
    )


@router.callback_query(RequestCreateStates.uploading_files, F.data == "cr:file:skip")
async def skip_files(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if is_session_expired(data):
        await reset_user_dialog(callback, state, reason_key="session_recovered", use_alert=True)
        return

    lang = await sync_to_async(get_user_bot_language)(callback.from_user.id if callback.from_user else 0)
    await state.update_data(
        attachments_meta=[],
        last_step_at=timezone.now().isoformat(),
    )
    preview = await _build_preview_text(state, lang)
    await state.set_state(RequestCreateStates.confirming)
    await callback.message.edit_text(preview, reply_markup=confirm_request_keyboard(lang))
    await callback.answer()


@router.callback_query(RequestCreateStates.uploading_files, F.data == "cr:file:done")
async def finish_files(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if is_session_expired(data):
        await reset_user_dialog(callback, state, reason_key="session_recovered", use_alert=True)
        return

    lang = await sync_to_async(get_user_bot_language)(callback.from_user.id if callback.from_user else 0)
    await state.update_data(last_step_at=timezone.now().isoformat())
    preview = await _build_preview_text(state, lang)
    await state.set_state(RequestCreateStates.confirming)
    await callback.message.edit_text(preview, reply_markup=confirm_request_keyboard(lang))
    await callback.answer()


@router.callback_query(RequestCreateStates.confirming, F.data == "cr:confirm")
async def confirm_request(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if is_session_expired(data):
        await reset_user_dialog(callback, state, reason_key="session_recovered", use_alert=True)
        return

    lang = await sync_to_async(get_user_bot_language)(callback.from_user.id if callback.from_user else 0)
    profile = await _require_verified_profile(callback)

    if not profile:
        await state.clear()
        await callback.message.answer(tr(lang, "verify_first"))
        await callback.answer()
        return

    company = getattr(profile, "company", None)
    if not company:
        await state.clear()
        await callback.message.answer(tr(lang, "verify_first"))
        await callback.answer()
        return

    problem_direction = await sync_to_async(get_problem_direction_by_id)(data["problem_direction_id"])

    company_ctx = await sync_to_async(get_company_request_context)(company.id)
    if not company_ctx:
        await state.clear()
        await callback.message.answer(tr(lang, "verify_first"))
        await callback.answer()
        return

    category = company_ctx["category"]
    region = company_ctx["region"]
    district = company_ctx["district"]
    directions = company_ctx["directions"]

    attachments_meta = data.get("attachments_meta", [])
    attachments = await download_telegram_attachments(callback.bot, attachments_meta)

    req = await sync_to_async(create_request_from_telegram_profile)(
        profile=profile,
        problem_direction=problem_direction,
        category=category,
        region=region,
        district=district,
        directions=directions,
        description=data["description"],
        attachments=attachments,
    )

    await notify_request_created(callback.bot, req.id)

    await state.clear()
    await callback.message.answer(
        tr(
            lang,
            "request_created_success",
            request_number=req.public_id or req.pk,
            status=translate_request_status(req.status, lang),
        ),
        reply_markup=main_menu_keyboard(lang),
    )
    await callback.answer()