# apps/panel/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _

from apps.agency.models import Department, Employee as AgencyEmployee


BASE_INPUT = "block w-full rounded-lg border border-gray-300 bg-gray-50 p-2.5 text-sm focus:border-blue-500 focus:ring-blue-500"
BASE_TEXTAREA = BASE_INPUT + " min-h-[120px]"


class ResolutionForm(forms.Form):
    text = forms.CharField(label=_("Текст для резолюции"), widget=forms.Textarea, required=True)
    target_department = forms.ModelChoiceField(
        label=_("Департамент"),
        queryset=Department.objects.filter(is_active=True).order_by("name"),
        required=False,
        empty_label=_("Не выбран"),
    )
    target_employee = forms.ModelChoiceField(
        label=_("Сотрудник"),
        queryset=AgencyEmployee.objects.filter(is_active=True).select_related("user", "department"),
        required=False,
        empty_label=_("Не выбран"),
    )
    due_date = forms.DateField(
        label=_("Срок исполнения"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["text"].widget.attrs.update({"class": BASE_TEXTAREA})
        self.fields["target_department"].widget.attrs.update({"class": BASE_INPUT + " appearance-none cursor-pointer"})
        self.fields["target_employee"].widget.attrs.update({"class": BASE_INPUT + " appearance-none cursor-pointer"})
        self.fields["due_date"].widget.attrs.update({"class": BASE_INPUT + " cursor-pointer",})


class StepForm(forms.Form):
    text = forms.CharField(label=_("Шаг работы"), widget=forms.Textarea, required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["text"].widget.attrs.update({"class": BASE_TEXTAREA})


class PanelRequestFilterForm(forms.Form):
    q = forms.CharField(label=_("Поиск"), required=False)
    status = forms.CharField(label=_("Статус"), required=False)
    overdue = forms.BooleanField(label=_("Просрочено"), required=False)
