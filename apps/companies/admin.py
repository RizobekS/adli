# apps/companies/admin.py
from dal import autocomplete
from dal_select2.widgets import ModelSelect2
from django import forms
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from modeltranslation.admin import TranslationAdmin
from import_export.admin import ImportExportModelAdmin
from .resources import CompanyResource

from .models import Category, Direction, Company, Position, EmployeeCompany, Region, District, Unit, CompanyPhone, \
    CompanyDirectionStat


@admin.register(Region)
class RegionAdmin(TranslationAdmin, admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")
    ordering = ("name",)


@admin.register(District)
class DistrictAdmin(TranslationAdmin, admin.ModelAdmin):
    list_display = ("name", "code", "region")
    list_select_related = ("region",)
    search_fields = ("name", "code", "region__name", "region__code")
    list_filter = ("region",)
    ordering = ("region__name", "name")
    autocomplete_fields = ("region",)


@admin.register(Category)
class CategoryAdmin(TranslationAdmin, admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)
    ordering = ("name",)
    readonly_fields = ("created_at",)


@admin.register(Direction)
class DirectionAdmin(TranslationAdmin, admin.ModelAdmin):
    list_display = ("title", "category", "created_at")
    list_select_related = ("category",)
    search_fields = ("title", "description", "category__name")
    list_filter = ("category", "created_at")
    ordering = ("category__name", "title")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("category",)


class EmployeeCompanyInline(admin.TabularInline):
    model = EmployeeCompany
    extra = 0
    fields = (
        "position",
        "first_name",
        "last_name",
        "middle_name",
        "phone",
        "email",
        "created_at",
    )
    readonly_fields = ("created_at",)
    autocomplete_fields = ("position",)
    show_change_link = True


@admin.register(Unit)
class UnitAdmin(TranslationAdmin, admin.ModelAdmin):
    list_display = ("name", "short_name", "created_at")
    search_fields = ("name", "short_name")
    ordering = ("name",)
    readonly_fields = ("created_at",)


class CompanyPhoneInline(admin.TabularInline):
    model = CompanyPhone
    extra = 0
    fields = ("phone", "kind", "is_primary")


class CompanyDirectionStatInline(admin.TabularInline):
    model = CompanyDirectionStat
    extra = 0
    fields = ("direction", "year", "unit", "quantity", "volume_bln_sum")
    autocomplete_fields = ("direction", "unit")


class CompanyAdminForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = "__all__"
        widgets = {
            "district": ModelSelect2(
                url="district-autocomplete",
                forward=["region"],
                attrs={"data-placeholder": "---------"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        data = self.data or {}
        region_id = data.get("region") or (self.instance.region_id if getattr(self.instance, "pk", None) else None)

        if region_id:
            self.fields["district"].queryset = (
                District.objects
                .filter(region_id=region_id)
                .order_by("code", "id")
            )
        else:
            # Нет выбранного блока — список секций пуст
            self.fields["district"].queryset = District.objects.none()

    def clean(self):
        cleaned = super().clean()
        region = cleaned.get("region")
        district = cleaned.get("district")
        # 2) Страховка: если пользователь как-то выбрал «чужую» секцию — отклоняем
        if region and district and district.region_id != region.id:
            self.add_error("district", "Район не принадлежит выбранному Региону.")
        return cleaned


@admin.register(Company)
class CompanyAdmin(TranslationAdmin, ImportExportModelAdmin, admin.ModelAdmin):
    resource_class = CompanyResource
    form = CompanyAdminForm
    list_display = ("name", "inn", "category", "region", "district", "number_of_jobs", "created_at")
    list_select_related = ("category", "region", "district",)
    search_fields = ("name", "inn", "description", "category__name", "region__name", "district__name",)
    list_filter = ("region", "district", "category", "created_at")
    ordering = ("name",)
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"
    inlines = (CompanyDirectionStatInline, EmployeeCompanyInline, CompanyPhoneInline,)

    fields = (
        "category",
        "categories",
        "directions",
        "region",
        "district",
        "name",
        "inn",
        "description",
        "number_of_jobs",
        "created_at",
    )

    filter_horizontal = ("categories", "directions",)
    autocomplete_fields = ("category", "region",)


@admin.register(Position)
class PositionAdmin(TranslationAdmin, admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)
    ordering = ("name",)
    list_filter = ("created_at",)
    readonly_fields = ("created_at",)


@admin.register(EmployeeCompany)
class EmployeeCompanyAdmin(admin.ModelAdmin):
    list_display = (
        "company",
        "position",
        "last_name",
        "first_name",
        "phone",
        "email",
        "created_at",
    )
    list_select_related = ("company", "position")
    search_fields = (
        "first_name",
        "last_name",
        "middle_name",
        "phone",
        "email",
        "company__name",
        "company__inn",
        "position__name",
    )
    list_filter = ("company", "position", "created_at")
    ordering = ("company", "position", "last_name", "first_name")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"
    autocomplete_fields = ("company", "position")

    fields = (
        "company",
        "position",
        "last_name",
        "first_name",
        "middle_name",
        "phone",
        "email",
        "created_at",
    )
