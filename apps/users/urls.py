from django.urls import path
from django.contrib.auth import views as auth_views
from .forms import StyledAuthenticationForm

app_name = "users"

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(
        template_name="users/login.html",
        authentication_form=StyledAuthenticationForm,
    ), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
