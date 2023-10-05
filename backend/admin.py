from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from backend.forms import CustomUserChangeForm, CustomUserCreationForm
from backend.models import Client


class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = Client
    list_display = (
        "email",
        "type",
        "is_active",
    )
    list_filter = (
        "email",
        "type",
        "is_active",
    )
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Permissions",
            {"fields": ("type", "is_active", "groups", "user_permissions")},
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "type",
                    "is_active",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
    )
    search_fields = ("email",)
    ordering = ("email",)


admin.site.register(Client, CustomUserAdmin)
