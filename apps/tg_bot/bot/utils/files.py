from __future__ import annotations

import os
from io import BytesIO

from django.core.files.base import ContentFile

MAX_ATTACH_MB = 10
MAX_ATTACH_BYTES = MAX_ATTACH_MB * 1024 * 1024

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".jpg", ".jpeg", ".png"}


def is_allowed_filename(filename: str) -> bool:
    ext = os.path.splitext((filename or "").lower())[1]
    return ext in ALLOWED_EXTENSIONS


def build_safe_photo_name(file_unique_id: str | None, fallback: str = "photo") -> str:
    suffix = file_unique_id or fallback
    return f"{suffix}.jpg"


async def download_telegram_attachments(bot, attachments_meta: list[dict]) -> list[ContentFile]:
    result: list[ContentFile] = []

    for item in attachments_meta:
        file_id = item["file_id"]
        filename = item["filename"]

        buffer = await bot.download(file_id)
        if buffer is None:
            continue

        if isinstance(buffer, BytesIO):
            buffer.seek(0)
            content = buffer.read()
        else:
            try:
                buffer.seek(0)
            except Exception:
                pass
            content = buffer.read()

        result.append(ContentFile(content, name=filename))

    return result