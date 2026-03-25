from datetime import datetime, timedelta, timezone

SESSION_TTL_MINUTES = 30


def is_session_expired(data: dict, ttl_minutes: int = SESSION_TTL_MINUTES) -> bool:
    value = data.get("last_step_at")
    if not value:
        return False

    try:
        dt = datetime.fromisoformat(value)
    except Exception:
        return False

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return datetime.now(timezone.utc) - dt > timedelta(minutes=ttl_minutes)