from django.contrib import admin

from .models import (
    Basin
)


@admin.register(Basin)
class BasinAdmin(admin.ModelAdmin):
    list_display = (
        "basin_id",
        "name",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
    )

    list_display_links = (
        "basin_id",
        "name",
    )

    search_fields = (
        "basin_id",
        "name",
    )

    ordering = ("-id",)
