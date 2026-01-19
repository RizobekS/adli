from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class TelephonyConfig(AppConfig):
    name = 'apps.telephony'
    verbose_name = _("IP телефония")

    def ready(self):
        from . import signals  # noqa
