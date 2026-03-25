import re


def normalize_uz_phone(raw: str) -> str:
    """
    Приводит номер к формату +998XXXXXXXXX

    Примеры:
    901234567 -> +998901234567
    998901234567 -> +998901234567
    +998901234567 -> +998901234567
    """
    if not raw:
        return ""

    digits = re.sub(r"\D+", "", str(raw))

    if not digits:
        return ""

    if digits.startswith("998") and len(digits) == 12:
        return f"+{digits}"

    if len(digits) == 9:
        return f"+998{digits}"

    if len(digits) == 12 and not digits.startswith("998"):
        return f"+{digits}"

    if len(digits) == 13 and digits.startswith("998"):
        return f"+{digits}"

    return f"+{digits}"


def phone_candidates(raw: str) -> list[str]:
    """
    Возвращает набор возможных представлений номера для поиска в БД.
    """
    normalized = normalize_uz_phone(raw)
    if not normalized:
        return []

    digits = normalized.replace("+", "")
    local = digits[3:] if digits.startswith("998") else digits

    values = {
        normalized,         # +998901234567
        digits,             # 998901234567
        local,              # 901234567
        f"+{local}",        # +901234567 (на всякий случай)
    }
    return [v for v in values if v]