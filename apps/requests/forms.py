from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.companies.models import Category, Direction, Region, District

BASE_INPUT = "block w-full rounded-lg border border-gray-300 bg-gray-50 p-2.5 text-sm focus:border-blue-500 focus:ring-blue-500"
BASE_TEXTAREA = BASE_INPUT + " min-h-[120px]"

MAX_MAIN_MB = 10
MAX_ATTACH_MB = 10

def validate_file_size(f, max_mb):
    if f.size > max_mb * 1024 * 1024:
        raise ValidationError(_("Файл слишком большой (макс. %(mb)s MB)."), params={"mb": max_mb})

class MultipleFileInput(forms.FileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        # data может быть list файлов
        if not data:
            return []
        if isinstance(data, (list, tuple)):
            return [super().clean(d, initial) for d in data]
        return [super().clean(data, initial)]

class PublicRequestForm(forms.Form):
    # company
    category = forms.ModelChoiceField(
        label=_("Категория"),
        queryset=Category.objects.all(),
        empty_label=_("Выберите категорию"),
    )
    company_name = forms.CharField(label=_("Название компании"), max_length=255)
    inn = forms.CharField(label=_("ИНН"), max_length=20)

    region = forms.ModelChoiceField(
        label=_("Регион"),
        queryset=Region.objects.all().order_by("name"),
        required=False,
        empty_label=_("Выберите регион"),
    )

    district = forms.ModelChoiceField(
        label=_("Район/город"),
        queryset=District.objects.none(),
        required=False,
        empty_label=_("Выберите район/город"),
    )

    # employee
    first_name = forms.CharField(label=_("Имя"), max_length=150)
    last_name = forms.CharField(label=_("Фамилия"), max_length=150)
    middle_name = forms.CharField(label=_("Отчество"), max_length=150, required=False)
    phone = forms.CharField(label=_("Телефон номер"), max_length=15)
    email = forms.EmailField(label=_("Электронная почта"))

    # request
    directions = forms.ModelMultipleChoiceField(
        label=_("Направления"),
        queryset=Direction.objects.none(),
        required=False,
    )

    description = forms.CharField(label=_("Текст обращения"), widget=forms.Textarea)

    attachments = MultipleFileField(label=_("Приложения"), required=False)

    def __init__(self, *args, **kwargs):
        directions_qs = kwargs.pop("directions_qs", Direction.objects.all())
        district_qs = kwargs.pop("district_qs", District.objects.none())
        super().__init__(*args, **kwargs)

        self.fields["directions"].queryset = directions_qs
        self.fields["district"].queryset = district_qs

        # классы
        for name in [
            "company_name", "inn", "region", "district",
            "first_name", "last_name", "middle_name",
            "phone", "email",
        ]:
            self.fields[name].widget.attrs.update({"class": BASE_INPUT})

        self.fields["category"].widget.attrs.update({"class": BASE_INPUT})
        self.fields["directions"].widget.attrs.update({"class": BASE_INPUT, "multiple": True})

        self.fields["description"].widget.attrs.update({"class": BASE_TEXTAREA})

        file_cls = "block w-full text-sm text-gray-900 border border-gray-300 rounded-lg p-2 cursor-pointer bg-gray-50"
        self.fields["attachments"].widget.attrs.update({
            "class": file_cls,
            "multiple": True,
            "accept": ".pdf,.doc,.docx,.xls,.xlsx"
        })

    def clean_attachments(self):
        files = self.cleaned_data.get("attachments") or []
        allowed = (".pdf", ".doc", ".docx", ".xls", ".xlsx")

        for item in files:
            validate_file_size(item, MAX_ATTACH_MB)
            if not item.name.lower().endswith(allowed):
                raise ValidationError(_("Разрешены только: PDF, Word, Excel."))
        return files

    def clean(self):
        cleaned = super().clean()
        region = cleaned.get("region")
        district = cleaned.get("district")
        if district and region and district.region_id != region.id:
            self.add_error("district", _("Выбранный район/город не относится к выбранному региону."))
        if district and not region:
            self.add_error("region", _("Сначала выберите регион."))
        return cleaned


class TrackRequestsForm(forms.Form):
    inn = forms.CharField(
        label=_("ИНН компании"),
        max_length=20,
    )
    public_id = forms.CharField(
        label=_("Номер обращения"),
        max_length=20,
        help_text=_("Формат: YYYY-000001"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ("inn", "public_id"):
            self.fields[f].widget.attrs.update({"class": BASE_INPUT})
