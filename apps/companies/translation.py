from modeltranslation.translator import register, TranslationOptions, translator
from django.utils.translation import gettext_lazy as _
from .models import Region, District, Category, Direction, Company, Position, Unit


@register(Region)
class RegionTR(TranslationOptions):
    fields = ("name",)
    fallback_values = '-- no translation --'


@register(District)
class DistrictTR(TranslationOptions):
    fields = ("name",)
    fallback_values = '-- no translation --'


@register(Category)
class CategoryTR(TranslationOptions):
    fields = ("name",)
    fallback_values = '-- no translation --'


@register(Direction)
class DirectionTR(TranslationOptions):
    fields = ("title", "description")
    fallback_values = '-- no translation --'


@register(Unit)
class UnitTR(TranslationOptions):
    fields = ("name", "short_name")
    fallback_values = '-- no translation --'


@register(Company)
class CompanyTR(TranslationOptions):
    fields = ("description",)
    fallback_values = '-- no translation --'


@register(Position)
class PositionTR(TranslationOptions):
    fields = ("name",)
    fallback_values = '-- no translation --'

