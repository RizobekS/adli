from functools import wraps
from django.http import Http404
from django.shortcuts import redirect

def agency_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        u = request.user
        if not u.is_authenticated:
            return redirect("users:login")
        # только сотрудники агентства
        if not hasattr(u, "agency_employee") or not u.agency_employee.is_active:
            raise Http404()
        return view_func(request, *args, **kwargs)
    return _wrapped


def public_company_only(view_func):
    """
    Публичные страницы доступны всем, но если это сотрудник агентства и он залогинен,
    то скрываем.
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        u = request.user
        if u.is_authenticated and hasattr(u, "agency_employee"):
            raise Http404()
        return view_func(request, *args, **kwargs)
    return _wrapped
