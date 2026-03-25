from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class TgBotConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tg_bot"
    verbose_name = _("Телеграм бот")
