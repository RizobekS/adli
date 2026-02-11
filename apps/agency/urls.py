from django.urls import path
from .views import public_home, public_about_detail, public_news_list, public_news_detail, public_announcements_list, \
    public_leadership_list

app_name = "agency"

urlpatterns = [
    path("", public_home, name="public_home"),
    path("about/", public_about_detail, name="public_about_detail"),
    path("leadership/", public_leadership_list, name="public_leadership_list"),
    path("news/", public_news_list, name="public_news_list"),
    path("news/<int:pk>/", public_news_detail, name="public_news_detail"),
    path("announcements/", public_announcements_list, name="public_announcements_list"),
]
