# apps/panel/services/request_buckets.py
from apps.requests.models import Request

GROUP_CHANCELLERY = "chancellery"
GROUP_DEPUTY_ASSISTANT = "deputy_assistant"
GROUP_EXECUTOR = "executor"
GROUP_DIRECTORS = "directors"
GROUP_HEAD_OF_DEPARTMENT = "head_of_department"


def _in_group(user, name: str) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return user.groups.filter(name=name).exists()


def visible_requests_qs(qs, user):
    """
    Ограничение видимости (как _filter_queryset_for_user в views).
    Принимает qs, чтобы не терять select_related/prefetch в view.
    """
    if _in_group(user, GROUP_CHANCELLERY) or _in_group(user, GROUP_DIRECTORS):
        return qs

    emp = getattr(user, "agency_employee", None)
    if not emp:
        return qs.none()

    if _in_group(user, GROUP_DEPUTY_ASSISTANT):
        return qs.filter(deputy_assistant=emp)

    if _in_group(user, GROUP_HEAD_OF_DEPARTMENT):
        return qs.filter(assigned_department=emp.department)

    if _in_group(user, GROUP_EXECUTOR):
        return qs.filter(assigned_employee=emp)

    return qs.none()


def apply_bucket(qs, user, bucket: str):
    """
    bucket: inbox|active|done|all
    new -> inbox (alias)
    """
    bucket = (bucket or "").strip()
    if bucket == "new":
        bucket = "inbox"

    if bucket == "all":
        return qs

    if bucket == "done":
        return qs.filter(status=Request.Status.DONE)

    if bucket == "inbox":
        if _in_group(user, GROUP_CHANCELLERY) or _in_group(user, GROUP_DIRECTORS):
            return qs.filter(status=Request.Status.NEW)

        if _in_group(user, GROUP_DEPUTY_ASSISTANT):
            return qs.filter(status=Request.Status.SENT_FOR_RESOLUTION)

        if _in_group(user, GROUP_HEAD_OF_DEPARTMENT):
            return qs.filter(status=Request.Status.ASSIGNED)

        if _in_group(user, GROUP_EXECUTOR):
            return qs.filter(status=Request.Status.ASSIGNED)

        return qs.none()

    if bucket == "active":
        if _in_group(user, GROUP_CHANCELLERY) or _in_group(user, GROUP_DIRECTORS):
            return qs.filter(status__in=[
                Request.Status.REGISTERED,
                Request.Status.SENT_FOR_RESOLUTION,
                Request.Status.ASSIGNED,
                Request.Status.IN_PROGRESS,
            ])

        if _in_group(user, GROUP_DEPUTY_ASSISTANT):
            return qs.filter(status__in=[
                Request.Status.ASSIGNED,
                Request.Status.IN_PROGRESS,
            ])

        if _in_group(user, GROUP_HEAD_OF_DEPARTMENT):
            return qs.filter(status=Request.Status.IN_PROGRESS)

        if _in_group(user, GROUP_EXECUTOR):
            return qs.filter(status=Request.Status.IN_PROGRESS)

        return qs.none()

    # неизвестный bucket → inbox
    return apply_bucket(qs, user, "inbox")


def bucket_counts(qs, user):
    """
    На будущее: числа для sidebar.
    Возвращаем counts по bucket-ам на основе УЖЕ ограниченного видимости qs.
    """
    base = visible_requests_qs(qs, user)
    return {
        "inbox": apply_bucket(base, user, "inbox").count(),
        "active": apply_bucket(base, user, "active").count(),
        "done": apply_bucket(base, user, "done").count(),
        "all": base.count(),
    }
