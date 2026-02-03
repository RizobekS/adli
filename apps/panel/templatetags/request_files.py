import os
from django import template

register = template.Library()

@register.filter
def basename(file_or_name):
    """
    Принимает FieldFile (a.file), строку пути или объект с .name
    """
    if not file_or_name:
        return ""
    name = getattr(file_or_name, "name", None) or str(file_or_name)
    return os.path.basename(name)

@register.filter
def ext(file_or_name):
    """
    Возвращает расширение (pdf, docx, ...)
    """
    if not file_or_name:
        return ""
    name = getattr(file_or_name, "name", None) or str(file_or_name)
    base = os.path.basename(name)
    parts = base.rsplit(".", 1)
    return (parts[1].lower() if len(parts) == 2 else "")
