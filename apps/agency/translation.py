from modeltranslation.translator import register, TranslationOptions
from .models import Department, PositionAgency, AgencyAbout, News, LeadershipProfile


@register(Department)
class DepartmentTR(TranslationOptions):
    fields = ("name",)
    fallback_values = '-- no translation --'


@register(PositionAgency)
class PositionAgencyTR(TranslationOptions):
    fields = ("name",)
    fallback_values = '-- no translation --'


@register(AgencyAbout)
class AgencyAboutTR(TranslationOptions):
    fields = ("title", "short_description", "description")
    fallback_values = '-- no translation --'


@register(News)
class NewsTR(TranslationOptions):
    fields = ("title", "description")
    fallback_values = '-- no translation --'


@register(LeadershipProfile)
class LeadershipProfileTR(TranslationOptions):
    fields = ("reception_time", "biography")
    fallback_values = '-- no translation --'
