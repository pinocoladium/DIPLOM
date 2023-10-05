from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from backend.models import Client


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = Client
        fields = ("email",)


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = Client
        fields = ("email",)
