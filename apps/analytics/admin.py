from django.contrib import admin

from .models import (
    RainfallEvent
)


@admin.register(RainfallEvent)
class RainfallEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "basin",
        "start_timestamp",
        "end_timestamp",
        "duration_hours",
        "peak_value",
        "total_volume",
        "min_dry_gap_used",
        "is_cold_event",
        "created_at",
    )

    list_display_links = (
        "id",
        "basin",
    )

    search_fields = (
        "basin__basin_id",
        "basin__name",
    )

    list_filter = (
        "is_cold_event",
        "min_dry_gap_used",
        "created_at",
    )

    ordering = ("-id",)