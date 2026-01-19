# apps/telephony/services.py
from __future__ import annotations
import secrets
import string
from django.utils import timezone
from typing import Any, Dict, List
from .kerio_client import KerioOperatorClient
from typing import Any, Dict, List
from apps.agency.models import Employee
from .models import TelephonyLink

from .crypto import encrypt_str



def fetch_kerio_users_with_numbers() -> List[Dict[str, Any]]:
    api = KerioOperatorClient()

    params = {
        "query": {
            "start": 0,
            "limit": -1,  # как в DevTools: -1 = все
            "orderBy": [{"columnName": "USERNAME", "direction": "Asc"}],
        }
    }

    result = api.call("Users.get", params)
    user_list = result.get("userList", []) or []

    cleaned: List[Dict[str, Any]] = []
    for u in user_list:
        exts = u.get("EXTENSIONS") or []
        tel_nums = []
        for e in exts:
            n = e.get("TEL_NUM")
            if n:
                tel_nums.append(str(n).strip())

        cleaned.append({
            "guid": u.get("GUID"),
            "username": u.get("USERNAME"),
            "full_name": (u.get("FULL_NAME") or "").strip(),
            "numbers": tel_nums,  # список номеров (может быть пустым)
            "disabled": bool(u.get("DISABLED", False)),
        })

    cleaned.sort(
        key=lambda x: (x["full_name"] == "", x["full_name"].lower())
    )
    return cleaned


def fetch_kerio_extensions() -> list[dict]:
    api = KerioOperatorClient()
    params = {"query": {"start": 0, "limit": -1, "orderBy": [{"columnName": "telNum", "direction": "Asc"}]}}
    result = api.call("Extensions.get", params)
    return result.get("extensionList") or result.get("list") or result.get("extensions") or []


def build_directory_rows() -> List[Dict[str, Any]]:
    # Kerio users -> индексы
    kerio_items = fetch_kerio_users_with_numbers()
    by_guid = {x["guid"]: x for x in kerio_items if x.get("guid") is not None}
    by_ext = {}
    for x in kerio_items:
        for n in x.get("numbers") or []:
            by_ext[str(n).strip()] = x

    rows: List[Dict[str, Any]] = []

    employees = (
        Employee.objects
        .select_related("user", "department", "position")
        .prefetch_related("telephony_link")
        .filter(is_active=True)
    )

    for emp in employees:
        link = getattr(emp, "telephony_link", None)

        extension = (link.extension if link else "") or ""
        kerio_guid = link.kerio_guid if link else None

        kerio = None
        if kerio_guid:
            kerio = by_guid.get(kerio_guid)
        if kerio is None and extension:
            kerio = by_ext.get(str(extension).strip())

        kerio_disabled = bool(kerio.get("disabled")) if kerio else False

        full_name = emp.user.get_full_name().strip() or emp.user.get_username()

        rows.append({
            "employee_id": emp.id,
            "photo": emp.photo.url if emp.photo else "",
            "full_name": full_name,
            "department": emp.department,
            "position": emp.position,
            "mobile_phone": emp.mobile_phone or "",
            "email": emp.email or emp.user.email or "",
            "extension": extension,
            "kerio_guid": kerio_guid,
            "kerio_disabled": kerio_disabled,
            "sip_last4": getattr(link, "sip_password_last4", "") if link else "",
        })

    # сортировка по ФИО
    rows.sort(key=lambda x: (x["full_name"] == "", x["full_name"].lower()))
    return rows


def _gen_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))

def kerio_create_extension(tel_num: str) -> dict:
    api = KerioOperatorClient()

    tel_num = str(tel_num).strip()

    params = {
        "detail": {
            "telNum": tel_num,
            "sipUsername": tel_num,
            "sipPassword": _gen_password(16),
            "description": "",
            "callPermission": 1,
            "userGuid": None,

            "dtmfMode": 0,
            "faxDetect": False,
            "faxDetectType": 0,
            "natSupport": False,
            "recordInbound": False,
            "recordOutbound": False,
            "secured": False,
        }
    }

    return api.call("Extensions.create", params)


def kerio_create_user_with_extension(link: TelephonyLink) -> dict:
    employee = link.employee

    full_name = employee.user.get_full_name().strip() or employee.user.get_username()
    username = (employee.user.username or "").strip() or f"emp_{employee.pk}"
    email = (employee.email or employee.user.email or "").strip()

    ext = str(link.extension).strip()
    if not ext:
        raise RuntimeError("TelephonyLink.extension is empty. Set internal number first.")

    pin = "".join(secrets.choice(string.digits) for _ in range(4))
    user_password = _gen_password(10) + "+1"  # Kerio любит спец-символы, ты уже видел "+"

    api = KerioOperatorClient()

    params = {
        "detail": {
            "LDAP_ENABLED": 0,
            "FULL_NAME": full_name,
            "EMAIL": email,
            "DISABLED": 0,
            "ADMINISTRATION_ROLE_ID": 2,
            "LANGUAGE_PBX": 1,
            "PIN": pin,
            "USERNAME": username,
            "USER_PASSWORD": user_password,
            "VOICEMAIL_DISABLED": False,
            "VOICEMAIL_PRESS0_ENABLED": False,
            "VOICEMAIL_PRESS0_TELNUM": "",
            "WEBRTC_ENABLED": True,
            "AMI_ENABLED": False,

            # ВАЖНО: назначаем внутренний номер тут же
            "EXTENSIONS": [
                {
                    "TEL_NUM": ext,
                    "DESCRIPTION": "",
                    "IS_PRIMARY": True,
                    "RING_EXTENSION": True,
                    "RING_EXTENSION_TIMEOUT": 15,
                    "VOICEMAIL_FALLBACK": True,
                    "VOICEMAIL_FALLBACK_TIMEOUT": 15,
                    "FIND_ME_LIST": [],
                }
            ],
        }
    }

    result = api.call("Users.create", params)

    kerio_guid = result.get("GUID") or result.get("guid") or result.get("userGuid")
    if kerio_guid is None:
        raise RuntimeError(f"Kerio Users.create returned no GUID. Result: {result}")

    link.kerio_guid = int(kerio_guid)
    link.kerio_username = username
    link.kerio_disabled = False
    link.last_sync_at = timezone.now()
    link.save(update_fields=["kerio_guid", "kerio_username", "kerio_disabled", "last_sync_at"])

    return {"kerio_guid": link.kerio_guid, "kerio_username": link.kerio_username}


def provision_employee_to_kerio(link: TelephonyLink) -> dict:
    """
    Полный PUSH:
    - если нет extension в Kerio, создаём его (Extensions.create)
    - создаём пользователя и назначаем extension (Users.create)
    - сохраняем GUID у себя
    """
    if link.kerio_guid:
        return {"status": "already_linked", "kerio_guid": link.kerio_guid}

    ext = str(link.extension).strip()
    if not ext:
        raise RuntimeError("Заполни внутренний номер (TelephonyLink.extension)")

    # попробуем создать extension; если уже существует, Kerio вернёт error
    # тогда можно либо ловить конкретный код ошибки, либо перед этим сделать Extensions.get и проверить.
    try:
        kerio_create_extension(ext)
    except Exception:
        # если номер уже существует — ок, идём дальше
        pass

    return kerio_create_user_with_extension(link)


def kerio_create_extension_for_link(link: TelephonyLink) -> dict:
    tel_num = str(link.extension).strip()
    sip_password = _gen_password(16)

    params = {
        "detail": {
            "telNum": tel_num,
            "sipUsername": tel_num,
            "sipPassword": sip_password,
            "description": "",
            "callPermission": 1,
            "userGuid": None,
            "dtmfMode": 0,
            "faxDetect": False,
            "faxDetectType": 0,
            "natSupport": False,
            "recordInbound": False,
            "recordOutbound": False,
            "secured": False,
        }
    }

    api = KerioOperatorClient()
    api.call("Extensions.create", params)

    link.sip_username = tel_num
    link.sip_password_enc = encrypt_str(sip_password)
    link.sip_password_last4 = sip_password[-4:]
    link.sip_password_set_at = timezone.now()
    link.save(update_fields=["sip_username", "sip_password_enc", "sip_password_last4", "sip_password_set_at"])

    return {"sip_username": tel_num, "sip_password": sip_password}


def pull_sync_kerio_links() -> dict:
    """
    PULL: обновляет kerio_guid/kerio_username/kerio_disabled по extension или по guid.
    """
    kerio_items = fetch_kerio_users_with_numbers()

    # index by guid and by extension
    by_guid = {x["guid"]: x for x in kerio_items if x.get("guid") is not None}
    by_ext = {}
    for x in kerio_items:
        for n in x.get("numbers") or []:
            by_ext[str(n).strip()] = x

    updated = 0
    now = timezone.now()

    for link in TelephonyLink.objects.select_related("employee", "employee__user"):
        src = None
        if link.kerio_guid:
            src = by_guid.get(link.kerio_guid)

        if src is None and link.extension:
            src = by_ext.get(str(link.extension).strip())

        if src is None:
            continue

        changed = False
        if not link.kerio_guid and src.get("guid") is not None:
            link.kerio_guid = int(src["guid"]); changed = True
        if src.get("username") and link.kerio_username != src["username"]:
            link.kerio_username = src["username"]; changed = True

        kerio_disabled = bool(src.get("disabled", False))
        if link.kerio_disabled != kerio_disabled:
            link.kerio_disabled = kerio_disabled; changed = True

        if changed:
            link.last_sync_at = now
            link.save(update_fields=["kerio_guid", "kerio_username", "kerio_disabled", "last_sync_at"])
            updated += 1

    return {"updated": updated, "total": len(kerio_items)}


