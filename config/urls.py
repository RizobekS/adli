from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from apps.companies.autocomplete import DistrictAutocomplete
from config.views import ActivateLanguageView

urlpatterns = [
                  path("admin/companies/district-autocomplete/", DistrictAutocomplete.as_view(), name="district-autocomplete"),
                  path('admin/', admin.site.urls),
                  path("i18n/", include("django.conf.urls.i18n")),
                  path("set_language/<str:lang>/", ActivateLanguageView.as_view(), name="set_language_from_url"),
    
                  path("", include("apps.users.urls")),

                  path("panel/", include("apps.panel.urls")),

                  path("", include("apps.companies.urls")),
                  path("", include("apps.requests.urls")),
                  path("", include("apps.telephony.urls")),

              ] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) \
              + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
