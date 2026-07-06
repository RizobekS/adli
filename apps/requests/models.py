# apps/requests/models.py
import os

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.companies.models import Company, EmployeeCompany, Direction
from apps.agency.models import Department, Employee as AgencyEmployee, ProblemDirection


def request_attach_upload_to(instance, filename):
    return os.path.join("requests", str(instance.request.company_id), "attachments", filename)


class RequestCounter(models.Model):
    year = models.PositiveIntegerField(_("Год"), unique=True)
    last_number = models.PositiveIntegerField(_("Последний номер"), default=0)

    class Meta:
        verbose_name = _("Счётчик обращений")
        verbose_name_plural = _("Счётчики обращений")

    def __str__(self):
        return f"{self.year}: {self.last_number}"


class Request(models.Model):
    class Status(models.TextChoices):
        NEW = "new", _("Новое")
        REGISTERED = "registered", _("Зарегистрировано (канцелярия)")
        SENT_FOR_RESOLUTION = "sent_for_resolution", _("На резолюции")
        ASSIGNED = "assigned", _("Назначено исполнителю")
        IN_PROGRESS = "in_progress", _("В работе")
        WAITING = "waiting", _("Ожидает ответа")
        DONE = "done", _("Обработано")
        CANCELLED = "cancelled", _("Отменено")

    class Source(models.TextChoices):
        PUBLIC_WEB = "public_web", _("Публичная форма")
        TELEGRAM = "telegram", _("Telegram bot")
        ADMIN_PANEL = "admin_panel", _("Админ панель")

    company = models.ForeignKey(
        Company,
        verbose_name=_("Компания"),
        on_delete=models.PROTECT,
        related_name="requests",
    )
    employee = models.ForeignKey(
        EmployeeCompany,
        verbose_name=_("Сотрудник компании"),
        on_delete=models.PROTECT,
        related_name="requests",
        null=True,
        blank=True,
    )
    telegram_profile = models.ForeignKey(
        "tg_bot.TelegramProfile",
        verbose_name=_("Telegram профиль заявителя"),
        on_delete=models.SET_NULL,
        related_name="requests",
        null=True,
        blank=True,
    )

    deputy_assistant = models.ForeignKey(
        AgencyEmployee,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="requests_as_deputy",
        verbose_name="Помощник руководителя"
    )

    directions = models.ManyToManyField(
        Direction,
        verbose_name=_("Направления"),
        related_name="requests",
        blank=True,
    )

    problem_direction = models.ForeignKey(
        ProblemDirection,
        verbose_name=_("Проблемное направление"),
        on_delete=models.PROTECT,
        related_name="requests",
        null=True,
        blank=True,
    )

    description = models.TextField(_("Текст обращения"))

    status = models.CharField(
        _("Статус"),
        max_length=32,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
    )

    public_id = models.CharField(
        _("Публичный номер"),
        max_length=20,
        unique=True,
        db_index=True,
        blank=True,
        editable=False,
        help_text=_("Формат: YYYY-000001"),
    )

    public_year = models.PositiveIntegerField(_("Год (публичный)"), null=True, blank=True, editable=False)
    public_seq = models.PositiveIntegerField(_("Порядковый номер (публичный)"), null=True, blank=True, editable=False)

    # Куда назначено (после резолюции)
    assigned_department = models.ForeignKey(
        Department,
        verbose_name=_("Назначенный департамент"),
        on_delete=models.PROTECT,
        related_name="assigned_requests",
        null=True,
        blank=True,
    )
    assigned_employee = models.ForeignKey(
        AgencyEmployee,
        verbose_name=_("Назначенный сотрудник"),
        on_delete=models.PROTECT,
        related_name="assigned_requests",
        null=True,
        blank=True,
    )

    due_date = models.DateField(
        _("Срок исполнения"),
        null=True,
        blank=True,
        help_text=_("Срок по резолюции/контролю"),
    )

    resolved_at = models.DateTimeField(_("Дата завершения"), null=True, blank=True)

    created_at = models.DateTimeField(_("Дата создания"), auto_now_add=True)

    source = models.CharField(
        _("Источник"),
        max_length=20,
        choices=Source.choices,
        default=Source.PUBLIC_WEB,
        db_index=True,
    )
    updated_at = models.DateTimeField(_("Дата обновления"), auto_now=True)

    class Meta:
        verbose_name = _("Обращение")
        verbose_name_plural = _("Обращения")
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["due_date"]),
        ]

    def __str__(self):
        return f"Обращение #{self.pk} — {self.company}"


class RequestFile(models.Model):
    class Kind(models.TextChoices):
        ATTACHMENT = "attachment", _("Приложение")

    request = models.ForeignKey(
        Request,
        verbose_name=_("Обращение"),
        on_delete=models.CASCADE,
        related_name="files",
    )
    kind = models.CharField(_("Тип"), max_length=20, choices=Kind.choices, default=Kind.ATTACHMENT)

    file = models.FileField(
        _("Файл"),
        upload_to=request_attach_upload_to,
        validators=[FileExtensionValidator(["pdf", "doc", "docx", "xls", "xlsx", "jpg", "jpeg", "png"])]
    )

    created_at = models.DateTimeField(_("Дата загрузки"), auto_now_add=True)

    class Meta:
        verbose_name = _("Файл обращения")
        verbose_name_plural = _("Файлы обращения")
        ordering = ("-created_at",)


class RequestResolution(models.Model):
    """
    Резолюция замдиректора/помощника: текст + срок + назначение.
    Можно создавать несколько резолюций (переназначения не теряются).
    """
    request = models.ForeignKey(
        Request,
        verbose_name=_("Обращение"),
        on_delete=models.CASCADE,
        related_name="resolutions",
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Автор резолюции"),
        on_delete=models.PROTECT,
        related_name="request_resolutions",
    )

    text = models.TextField(_("Резолюция"))

    target_department = models.ForeignKey(
        Department,
        verbose_name=_("Департамент"),
        on_delete=models.PROTECT,
        related_name="resolutions",
        null=True,
        blank=True,
    )
    target_employee = models.ForeignKey(
        AgencyEmployee,
        verbose_name=_("Сотрудник"),
        on_delete=models.PROTECT,
        related_name="resolutions",
        null=True,
        blank=True,
    )

    due_date = models.DateField(_("Срок исполнения"), null=True, blank=True)

    created_at = models.DateTimeField(_("Дата резолюции"), auto_now_add=True)

    class Meta:
        verbose_name = _("Резолюция")
        verbose_name_plural = _("Резолюции")
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["due_date"]),
        ]

    def __str__(self):
        return f"Резолюция по обращению #{self.request_id}"


class RequestStep(models.Model):
    """
    Шаги работы исполнителя/департамента.
    Это “живой журнал” действий по обращению (не путать с аудит-историей статусов).
    """
    request = models.ForeignKey(
        Request,
        verbose_name=_("Обращение"),
        on_delete=models.CASCADE,
        related_name="steps",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Автор шага"),
        on_delete=models.PROTECT,
        related_name="request_steps",
    )
    text = models.TextField(_("Описание шага"))
    created_at = models.DateTimeField(_("Дата шага"), auto_now_add=True)

    class Meta:
        verbose_name = _("Шаг по обращению")
        verbose_name_plural = _("Шаги по обращению")
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Шаг #{self.pk} по обращению #{self.request_id}"

    @property
    def author_display(self):
        if hasattr(self.author, "agency_employee"):
            return self.author.agency_employee.display_name
        return self.author.get_username()


class RequestOfficialResponse(models.Model):
    """
    Текст официального ответа и состояние доставки заявителю.
    """

    class DeliveryStatus(models.TextChoices):
        PENDING = "pending", _("Ожидает отправки")
        SENT = "sent", _("Отправлено")
        FAILED = "failed", _("Ошибка")
        SKIPPED = "skipped", _("Пропущено")

    request = models.ForeignKey(
        Request,
        verbose_name=_("Обращение"),
        on_delete=models.CASCADE,
        related_name="official_responses",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Автор ответа"),
        on_delete=models.PROTECT,
        related_name="request_official_responses",
    )
    telegram_profile = models.ForeignKey(
        "tg_bot.TelegramProfile",
        verbose_name=_("Telegram профиль получателя"),
        on_delete=models.SET_NULL,
        related_name="official_responses",
        null=True,
        blank=True,
    )

    recipient_email = models.EmailField(_("Email получателя"), blank=True)
    subject = models.CharField(_("Тема письма"), max_length=255)
    text = models.TextField(_("Текст ответа"))

    email_status = models.CharField(
        _("Статус email"),
        max_length=20,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
        db_index=True,
    )
    telegram_status = models.CharField(
        _("Статус Telegram"),
        max_length=20,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.SKIPPED,
        db_index=True,
    )
    email_error = models.TextField(_("Ошибка email"), blank=True)
    telegram_error = models.TextField(_("Ошибка Telegram"), blank=True)

    email_sent_at = models.DateTimeField(_("Дата отправки email"), null=True, blank=True)
    telegram_sent_at = models.DateTimeField(_("Дата отправки Telegram"), null=True, blank=True)

    created_at = models.DateTimeField(_("Дата создания"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Дата обновления"), auto_now=True)

    class Meta:
        verbose_name = _("Официальный ответ")
        verbose_name_plural = _("Официальные ответы")
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["request", "created_at"]),
        ]

    def __str__(self):
        return f"Официальный ответ #{self.pk} по обращению #{self.request_id}"


class RequestHistory(models.Model):
    """
    История действий (аудит): смена статусов, назначений, служебные комментарии.
    """
    class Action(models.TextChoices):
        CREATED = "created", _("Создано")
        REGISTERED = "registered", _("Зарегистрировано")
        SENT_FOR_RESOLUTION = "sent_for_resolution", _("Отправлено на резолюцию")
        RESOLVED = "resolved", _("Резолюция поставлена")
        ASSIGNED = "assigned", _("Назначено")
        STATUS_CHANGED = "status_changed", _("Статус изменён")
        STEP_ADDED = "step_added", _("Добавлен шаг")
        FILE_ADDED = "file_added", _("Добавлен файл")
        OFFICIAL_RESPONSE = "official_response", _("Официальный ответ")
        DONE = "done", _("Завершено")
        OTHER = "other", _("Другое")

    request = models.ForeignKey(
        Request,
        verbose_name=_("Обращение"),
        on_delete=models.CASCADE,
        related_name="history",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Кто сделал"),
        on_delete=models.PROTECT,
        related_name="request_history_actions",
        null=True,
        blank=True,
    )

    action = models.CharField(_("Действие"), max_length=32, choices=Action.choices, db_index=True)

    from_status = models.CharField(_("Статус до"), max_length=32, blank=True)
    to_status = models.CharField(_("Статус после"), max_length=32, blank=True)

    comment = models.TextField(_("Комментарий"), blank=True)

    created_at = models.DateTimeField(_("Дата действия"), auto_now_add=True)

    class Meta:
        verbose_name = _("История обращения")
        verbose_name_plural = _("История обращений")
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["action"]),
        ]

    def __str__(self):
        return f"История #{self.pk} по обращению #{self.request_id}"
