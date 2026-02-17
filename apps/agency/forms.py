from ckeditor.widgets import CKEditorWidget
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms

from apps.agency.models import News, LeadershipProfile, AgencyAbout


class AgencyAboutAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    class Meta:
        exclude = tuple()
        widgets = {
            'description': CKEditorWidget(),
        }
        model = AgencyAbout


class NewsAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    class Meta:
        exclude = tuple()
        widgets = {
            'description': CKEditorUploadingWidget(),
        }
        model = News