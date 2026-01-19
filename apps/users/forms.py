from django import forms
from django.contrib.auth.forms import AuthenticationForm

INPUT_CLS = "w-full rounded-xl border border-gray-200 bg-white/70 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-200"

class StyledAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Логин",
        widget=forms.TextInput(attrs={
            "class": INPUT_CLS,
            "autocomplete": "username",
            "placeholder": "username",
        }),
    )
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={
            "class": INPUT_CLS,
            "autocomplete": "current-password",
            "placeholder": "••••••••",
        }),
    )
