from django.db import models


class TelegramProfile(models.Model):
    """
    основная рабочая привязка идет через employee_company
    company это удобный кэш/shortcut
    """

    class BotLanguage(models.TextChoices):
        RU = "ru", "Русский"
        UZ = "uz", "O'zbekcha"

    telegram_user_id = models.BigIntegerField(unique=True, db_index=True)
    chat_id = models.BigIntegerField(db_index=True)

    username = models.CharField(max_length=255, blank=True)
    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    language_code = models.CharField(max_length=16, blank=True)

    bot_language = models.CharField(
        max_length=8,
        choices=BotLanguage.choices,
        default=BotLanguage.RU,
        db_index=True,
    )

    phone = models.CharField(max_length=20, blank=True)
    phone_normalized = models.CharField(max_length=20, blank=True, db_index=True)

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="telegram_profiles",
    )
    employee_company = models.ForeignKey(
        "companies.EmployeeCompany",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="telegram_profiles",
    )

    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Telegram профиль"
        verbose_name_plural = "Telegram профили"

    def __str__(self):
        return f"{self.telegram_user_id} | {self.phone_normalized or '-'}"


class TelegramChatBinding(models.Model):
    class ChatType(models.TextChoices):
        GROUP = "group", "Group"
        SUPERGROUP = "supergroup", "Supergroup"

    title = models.CharField(max_length=255, blank=True)
    chat_id = models.BigIntegerField(unique=True, db_index=True)
    chat_type = models.CharField(max_length=20, choices=ChatType.choices, default=ChatType.GROUP)
    is_active = models.BooleanField(default=True)

    department = models.ForeignKey(
        "agency.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="telegram_chat_bindings",
    )

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Telegram группа"
        verbose_name_plural = "Telegram группы"

    def __str__(self):
        return self.title or str(self.chat_id)