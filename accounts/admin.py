from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


# Register your models here.
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    ordering = ('email',)

    list_display = (
        "email",
        "first_name",
        "last_name",
        "is_active",
        "is_staff"
    )

    search_fields = (
        "email",
        "first_name",
        "last_name"
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "email",
                    "password"
                )
            }
        ),
        (
            "Personal Info",
            {
                "fields": (
                    "first_name",
                    "last_name"
                )
            }
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions"
                )
            }
        ),
        (
            "Important Dates",
            {
                "fields": (
                    "last_login",
                    "date_joined"
                )
            }
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "usable_password",
                    "password1",
                    "password2",
                    "is_active",
                    "is_staff",
                    "is_superuser"
                )
            }
        ),
    )