from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class AgencyConfig(AppConfig):
    name = 'apps.agency'
    verbose_name = _("Агентство")
