from modeltranslation.translator import register, TranslationOptions
from django.utils.translation import gettext_lazy as _
from .models import Department, Employee, PositionAgency


@register(Department)
class DepartmentTR(TranslationOptions):
    fields = ("name",)
    fallback_values = '-- no translation --'


@register(PositionAgency)
class PositionAgencyTR(TranslationOptions):
    fields = ("name",)
    fallback_values = '-- no translation --'
