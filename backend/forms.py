from django.contrib.auth.forms import UserCreationForm, UserChangeForm

from backend.models import Client


class CustomUserCreationForm(UserCreationForm):

    class Meta:
        model = Client
        fields = ("email",)


class CustomUserChangeForm(UserChangeForm):

    class Meta:
        model = Client
        fields = ("email",)