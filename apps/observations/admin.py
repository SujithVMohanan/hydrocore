from django.contrib import admin

from .models import (
    MeasurementType,
    Observation,
)


@admin.register(MeasurementType)
class MeasurementTypeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "unit",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
    )

    list_display_links = (
        "id",
        "name",
    )

    search_fields = (
        "name",
        "unit",
    )

    list_filter = (
        "unit",
        "created_at",
        "updated_at",
    )

    ordering = ("-id",)



@admin.register(Observation)
class ObservationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "basin",
        "measurement_type",
        "value",
        "timestamp",
        "source",
        "created_by",
        "created_at",
    )

    list_display_links = (
        "id",
        "basin",
    )

    search_fields = (
        "basin__basin_id",
        "basin__name",
        "measurement_type__name",
        "source",
    )

    list_filter = (
        "measurement_type",
        "source",
    )

    ordering = ("-id",)
