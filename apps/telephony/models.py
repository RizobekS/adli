from django.db import models
from django.utils.translation import gettext_lazy as _

class TelephonyLink(models.Model):
    employee = models.OneToOneField(
        "agency.Employee",
        on_delete=models.CASCADE,
        related_name="telephony_link",
        verbose_name=_("Сотрудник")
    )

    # Главный идентификатор Kerio (стабильный)
    kerio_guid = models.IntegerField(_("Kerio GUID"), null=True, blank=True, db_index=True, unique=True)

    # Удобно хранить, но НЕ использовать как ключ
    kerio_username = models.CharField(_("Kerio username"), max_length=150, blank=True)

    # Внутренний номер (может быть 1..N, но на практике у вас чаще 1)
    extension = models.CharField(_("Внутренний номер"), max_length=32, blank=True, db_index=True)

    # для мониторинга
    kerio_disabled = models.BooleanField(_("Отключён в Kerio"), default=False)
    last_sync_at = models.DateTimeField(_("Последняя синхронизация"), null=True, blank=True)

    sip_username = models.CharField(_("SIP логин"), max_length=64, blank=True)
    sip_password_enc = models.TextField(_("SIP пароль (зашифрованный)"), blank=True)
    sip_password_last4 = models.CharField(_("SIP пароль (последние 4)"), max_length=4, blank=True)
    sip_password_set_at = models.DateTimeField(_("SIP пароль установлен"), null=True, blank=True)

    class Meta:
        verbose_name = _("Связка с телефонией")
        verbose_name_plural = _("Связки с телефонией")

    def __str__(self):
        return f"{self.employee_id} -> {self.kerio_guid or '-'}"
