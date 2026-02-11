from django.core.exceptions import ValidationError
from django.db import models
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _

class Region(models.Model):
    code = models.CharField(_("Код региона"), max_length=10, unique=True, db_index=True)
    name = models.CharField(_("Название региона"), max_length=255)

    class Meta:
        verbose_name = _("Регион")
        verbose_name_plural = _("Регионы")
        ordering = ("name",)

    def __str__(self):
        return f"{self.name} ({self.code})"


class District(models.Model):
    region = models.ForeignKey(
        Region,
        verbose_name=_("Регион"),
        on_delete=models.PROTECT,
        related_name="districts",
    )
    code = models.CharField(_("Код района/города"), max_length=10, unique=True, db_index=True)
    name = models.CharField(_("Название района/города"), max_length=255)

    class Meta:
        verbose_name = _("Район/город")
        verbose_name_plural = _("Районы/города")
        ordering = ("region__name", "name")
        indexes = [
            models.Index(fields=["region", "name"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"


class Category(models.Model):
    name = models.CharField(_("Название категории"), max_length=255)
    created_at = models.DateTimeField(_("Дата создания"), auto_now_add=True)

    class Meta:
        verbose_name = _("Категория")
        verbose_name_plural = _("Категории")
        ordering = ("name",)
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return self.name


class Direction(models.Model):
    category = models.ForeignKey(
        Category,
        verbose_name=_("Категория"),
        on_delete=models.CASCADE,
        related_name="directions",
        null=True
    )
    title = models.CharField(_("Название"), max_length=255)
    description = models.TextField(_("Описание"), blank=True)
    created_at = models.DateTimeField(_("Дата создания"), auto_now_add=True)

    class Meta:
        verbose_name = _("Направление")
        verbose_name_plural = _("Направления")
        ordering = ("-created_at",)

    def __str__(self):
        return self.title


class Unit(models.Model):
    name = models.CharField(_("Единица измерения"), max_length=100)
    short_name = models.CharField(_("Сокращение"), max_length=30, blank=True)

    created_at = models.DateTimeField(_("Дата создания"), auto_now_add=True)

    class Meta:
        verbose_name = _("Единица измерения")
        verbose_name_plural = _("Единицы измерения")
        ordering = ("name",)
        indexes = [models.Index(fields=["name"])]

    def __str__(self):
        return self.short_name or self.name



class Company(models.Model):
    region = models.ForeignKey(
        Region,
        verbose_name=_("Регион"),
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="companies",
    )
    district = models.ForeignKey(
        District,
        verbose_name=_("Район/город"),
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="companies",
    )
    category = models.ForeignKey(
        Category,
        verbose_name=_("Категория"),
        on_delete=models.PROTECT,
        related_name="companies",
        null=True
    )
    categories = models.ManyToManyField(
        "companies.Category",
        blank=True,
        related_name="companies_m2m",
        verbose_name=_("Категории (множественные)"),
    )

    directions = models.ManyToManyField(
        Direction,
        verbose_name=_("Направления"),
        blank=True,
        related_name="companies"
    )
    name = models.CharField(_("Название компании"), max_length=255)
    inn = models.CharField(
        _("ИНН"),
        max_length=20,
        unique=True,
        help_text=_("Идентификационный номер налогоплательщика компании"),
    )

    description = models.TextField(
        _("Описание (о компании/доп. сведения)"),
        blank=True,
        help_text=_("Если нужно хранить доп. информацию о компании/отправителе"),
    )

    number_of_jobs = models.IntegerField(_("Количество рабочих мест"), blank=True, null=True)

    created_at = models.DateTimeField(_("Дата создания"), auto_now_add=True)

    class Meta:
        verbose_name = _("Компания")
        verbose_name_plural = _("Компании")
        ordering = ("name",)
        indexes = [
            models.Index(fields=["inn"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.inn})"

    def clean(self):
        super().clean()
        if self.region_id and self.district_id:
            if self.district.region_id != self.region_id:
                raise ValidationError({"district": _("Выбранный район/город не относится к выбранному региону.")})

class CompanyDirectionStat(models.Model):
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="direction_stats",
        verbose_name=_("Компания"),
    )
    direction = models.ForeignKey(
        "companies.Direction",
        on_delete=models.PROTECT,
        related_name="company_stats",
        verbose_name=_("Направление"),
    )
    year = models.PositiveSmallIntegerField(_("Год"))
    unit = models.ForeignKey(
        "companies.Unit",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Единица измерения"),
    )
    quantity = models.DecimalField(_("Количество"), max_digits=20, decimal_places=6, null=True, blank=True)
    volume_bln_sum = models.DecimalField(_("Объём (млрд сум)"), max_digits=20, decimal_places=6, null=True, blank=True)

    class Meta:
        verbose_name = _("Показатель компании по направлению")
        verbose_name_plural = _("Показатели компаний по направлениям")
        constraints = [
            models.UniqueConstraint(fields=["company", "direction", "year"], name="uniq_company_direction_year")
        ]


class Position(models.Model):
    name = models.CharField(_("Название должности"), max_length=255)

    created_at = models.DateTimeField(_("Дата создания"), auto_now_add=True)

    class Meta:
        verbose_name = _("Должность")
        verbose_name_plural = _("Должности")
        ordering = ("name",)

    def __str__(self):
        return self.name


class EmployeeCompany(models.Model):
    company = models.ForeignKey(
        Company,
        verbose_name=_("Компания"),
        on_delete=models.CASCADE,
        related_name="employee_company"
    )
    position = models.ForeignKey(
        Position,
        verbose_name=_("Должность"),
        on_delete=models.PROTECT,
        related_name="employee_company",
        null=True,
        blank=True,
    )

    first_name = models.CharField(_("Имя"), max_length=150, null=True)
    last_name = models.CharField(_("Фамилия"), max_length=150, null=True)
    middle_name = models.CharField(_("Отчество"), max_length=150, blank=True, null=True)
    phone = models.CharField(_("Телефон номер"), max_length=15, blank=True, null=True)
    email = models.EmailField(_("Электронная почта"), blank=True, null=True)

    created_at = models.DateTimeField(_("Дата создания"), auto_now_add=True)

    class Meta:
        verbose_name = _("Сотрудник компании")
        verbose_name_plural = _("Сотрудники компании")
        ordering = ("company", "position", "last_name", "first_name")
        constraints = [
            models.UniqueConstraint(
                fields=["company", "position", "last_name", "first_name", "middle_name"],
                name="uniq_employee_company_identity",
            )
        ]


    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.company}-{self.position})"


class CompanyPhone(models.Model):
    class Kind(models.TextChoices):
        MAIN = "main", _("Основной")
        MOBILE = "mobile", _("Мобильный")
        OFFICE = "office", _("Офис")
        OTHER = "other", _("Другое")

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="phones",
        verbose_name=_("Компания"),
    )
    phone = models.CharField(_("Телефон"), max_length=32, db_index=True)
    kind = models.CharField(_("Тип"), max_length=16, choices=Kind.choices, default=Kind.OTHER)
    is_primary = models.BooleanField(_("Основной номер"), default=False)

    class Meta:
        verbose_name = _("Телефон компании")
        verbose_name_plural = _("Телефоны компании")
        constraints = [
            models.UniqueConstraint(fields=["company", "phone"], name="uniq_company_phone"),
        ]

    def __str__(self):
        return f"{self.phone}"
