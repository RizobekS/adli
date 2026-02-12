# apps/panel/context_processors.py
from apps.panel.views import (
    _in_group,
    GROUP_CHANCELLERY,
    GROUP_DEPUTY_ASSISTANT,
    GROUP_EXECUTOR,
    GROUP_DIRECTORS,
    GROUP_HEAD_OF_DEPARTMENT,
)

def panel_nav_context(request):
    bucket = (request.GET.get("bucket") or "").strip()
    if bucket == "new":
        bucket = "inbox"

    return {
        "bucket": bucket,  # чтобы подсветка работала в sidebar на ЛЮБОЙ странице
        "is_chancellery": _in_group(request.user, GROUP_CHANCELLERY),
        "is_deputy_assistant": _in_group(request.user, GROUP_DEPUTY_ASSISTANT),
        "is_executor": _in_group(request.user, GROUP_EXECUTOR),
        "is_directors": _in_group(request.user, GROUP_DIRECTORS),
        "is_head_of_department": _in_group(request.user, GROUP_HEAD_OF_DEPARTMENT),
        "active_url": getattr(request.resolver_match, "url_name", ""),
        "active_ns": getattr(request.resolver_match, "namespace", ""),
    }
