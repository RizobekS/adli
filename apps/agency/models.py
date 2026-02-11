# apps/agency/models.py
from django.conf import settings
from django.db import models
from django.db.models import F
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Department(models.Model):
    name = models.CharField(_("Название департамента"), max_length=255, unique=True)
    code = models.CharField(
        _("Код"),
        max_length=50,
        blank=True,
        help_text=_("Опционально: короткий код департамента, например LEG, IT, HR")
    )
    is_active = models.BooleanField(_("Активен"), default=True)
    created_at = models.DateTimeField(_("Дата создания"), auto_now_add=True)

    class Meta:
        verbose_name = _("Департамент")
        verbose_name_plural = _("Департаменты")
        ordering = ("name",)
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return self.name


class PositionAgency(models.Model):
    name = models.CharField(_("Название должности"), max_length=255)

    created_at = models.DateTimeField(_("Дата создания"), auto_now_add=True)

    class Meta:
        verbose_name = _("Должность для агенства")
        verbose_name_plural = _("Должности для агенства")
        ordering = ("name",)

    def __str__(self):
        return self.name


class Employee(models.Model):
    """
    Внутренний сотрудник агентства (не путать с EmployeeCompany из apps.companies).
    Роли пока делаем через Django Groups (auth.Group).
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Пользователь"),
        on_delete=models.CASCADE,
        related_name="agency_employee",
    )

    department = models.ForeignKey(
        Department,
        verbose_name=_("Департамент"),
        on_delete=models.PROTECT,
        related_name="employees",
        null=True,
        blank=True,
    )

    position = models.ForeignKey(
        PositionAgency,
        verbose_name = _("Должность (в агентстве)"),
        on_delete=models.PROTECT,
        related_name="employees",
        blank=True,
        null=True,
    )

    first_name = models.CharField(_("Имя"), max_length=50, null=True)
    last_name = models.CharField(_("Фамилия"), max_length=50, null=True)
    middle_name = models.CharField(_("Отчество"), max_length=70, null=True, blank=True)

    pinpp = models.CharField(_("ПИНФЛ"), max_length=14, null=True, blank=True)

    phone = models.CharField(_("Телефон"), max_length=50, blank=True)

    photo = models.ImageField(_("Фото"), upload_to="agency/employees/", blank=True, null=True)
    mobile_phone = models.CharField(_("Сотовый телефон"), max_length=50, blank=True)
    email = models.EmailField(_("Email"), blank=True)

    is_active = models.BooleanField(_("Активен"), default=True)

    created_at = models.DateTimeField(_("Дата создания"), auto_now_add=True)

    class Meta:
        verbose_name = _("Сотрудник агентства")
        verbose_name_plural = _("Сотрудники агентства")
        ordering = ("department__name", "user__username")
        indexes = [
            models.Index(fields=["is_active"]),
        ]

    def _build_full_name(self) -> str:
        parts = [
            (self.last_name or "").strip(),
            (self.first_name or "").strip(),
            (self.middle_name or "").strip(),
        ]
        return " ".join([p for p in parts if p]).strip()

    @property
    def full_name(self) -> str:
        return self._build_full_name()

    @property
    def display_name(self) -> str:
        """
        Для UI: ФИО, иначе username.
        """
        fn = self.full_name
        if fn:
            return fn
        # get_username() корректнее чем .username, если кастомный user
        return self.user.get_username()

    @property
    def display_label(self) -> str:
        """
        То же самое + департамент (когда надо красиво в списках).
        """
        dep = self.department.name if self.department else ""
        return f"{self.display_name} ({dep})" if dep else self.display_name

    def __str__(self):
        return self.display_label


class AgencyAbout(models.Model):
    """
    Контент 'О агентстве' (обычно 1 запись).
    """
    title = models.CharField(_("Заголовок"), max_length=255)
    short_description = models.TextField(_("Краткое описание"), blank=True, null=True)
    description = models.TextField(_("Описание"), blank=True)

    photo = models.ImageField(_("Фото"), upload_to="agency/about/", blank=True, null=True)

    views_count = models.PositiveBigIntegerField(_("Просмотры"), default=0, db_index=True)

    is_published = models.BooleanField(_("Опубликовано"), default=True)
    created_at = models.DateTimeField(_("Создано"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Обновлено"), auto_now=True)

    class Meta:
        verbose_name = _("О агентстве")
        verbose_name_plural = _("О агентстве")
        ordering = ("-updated_at",)

    def __str__(self):
        return self.title

    @classmethod
    def get_public(cls):
        # Берём самую свежую опубликованную запись
        return cls.objects.filter(is_published=True).order_by("-updated_at").first()

    def inc_views(self):
        type(self).objects.filter(pk=self.pk).update(views_count=F("views_count") + 1)
        # обновим объект в памяти (не обязательно, но приятно)
        self.views_count += 1


class LeadershipProfile(models.Model):
    """
    Публичный профиль руководства (витрина для сайта),
    привязан к сотруднику Employee.
    """
    employee = models.OneToOneField(
        "agency.Employee",
        verbose_name=_("Сотрудник"),
        on_delete=models.CASCADE,
        related_name="leadership_profile",
    )

    is_published = models.BooleanField(_("Опубликовано"), default=True, db_index=True)
    sort_order = models.PositiveIntegerField(_("Порядок"), default=100, db_index=True)

    public_email = models.EmailField(_("Почта (публичная)"), blank=True)
    public_site_url = models.URLField(_("Ссылка на сайт"), blank=True)

    reception_time = models.CharField(
        _("Время приема"),
        max_length=255,
        blank=True,
        help_text=_("Например: Понедельник 10:00–13:00"),
    )

    biography = models.TextField(_("Биография"), blank=True)

    views_count = models.PositiveBigIntegerField(_("Просмотры"), default=0, db_index=True)

    created_at = models.DateTimeField(_("Создано"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Обновлено"), auto_now=True)

    class Meta:
        verbose_name = _("Профиль руководства")
        verbose_name_plural = _("Руководство")
        ordering = ("sort_order", "employee__last_name", "employee__first_name")
        indexes = [
            models.Index(fields=["is_published", "sort_order"]),
        ]

    def __str__(self):
        return self.employee.display_name

    def inc_views(self):
        type(self).objects.filter(pk=self.pk).update(views_count=F("views_count") + 1)
        self.views_count += 1


class News(models.Model):
    title = models.CharField(_("Заголовок"), max_length=255)
    description = models.TextField(_("Описание"), blank=True)

    photo = models.ImageField(_("Фото"), upload_to="agency/news/", blank=True, null=True)

    views_count = models.PositiveBigIntegerField(_("Просмотры"), default=0, db_index=True)

    announcement = models.BooleanField(_("Объявление"), default=False)
    is_published = models.BooleanField(_("Опубликовано"), default=True)
    published_at = models.DateTimeField(_("Дата публикации"), default=timezone.now, db_index=True)

    created_at = models.DateTimeField(_("Создано"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Обновлено"), auto_now=True)

    class Meta:
        verbose_name = _("Новость")
        verbose_name_plural = _("Новости")
        ordering = ("-published_at", "-id")
        indexes = [
            models.Index(fields=["is_published", "published_at", "announcement"]),
        ]

    def __str__(self):
        return self.title

    def inc_views(self):
        type(self).objects.filter(pk=self.pk).update(views_count=F("views_count") + 1)
        self.views_count += 1

