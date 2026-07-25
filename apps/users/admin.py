from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from apps.users.models import Users


@admin.register(Users)
class CustomUserAdmin(UserAdmin):
    model = Users

    list_display = (
        "id",
        "full_name",
        "email",
        "phone_number",
        "is_staff",
        "is_active",
        "created_at",
    )

    search_fields = (
        "email",
        "full_name",
        "phone_number",
    )

    ordering = ("-id",)

    readonly_fields = (
        "created_at",
        "updated_at",
        "last_login",
    )

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("full_name", "phone_number", "profile_image")}),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Important dates"), {"fields": ("last_login", "created_at", "updated_at")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2"),
        }),
    )

    filter_horizontal = ("groups", "user_permissions")