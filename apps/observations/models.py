from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.users.models import (
    BaseTimeStamps
)


class MeasurementType(BaseTimeStamps):
    
    name = models.CharField(
        _("Measurement Type"),
        max_length=50,
        db_index=True,
        help_text=_("Unique measurement type name"),
    )

    unit = models.CharField(
        _("Unit"),
        max_length=20,
        help_text=_("Measurement unit (e.g., mm, °C, m/s)"),
    )


    created_by = models.ForeignKey(
        "users.Users",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="measurement_types_created",
    )


    updated_by = models.ForeignKey(
        "users.Users",  
        on_delete=models.SET_NULL,
        null=True,
        blank=True, 
        related_name="measurement_types_updated",
    )


    class Meta:
        db_table = "measurement_types"
        ordering = ("-id",)

        indexes = [
            models.Index(fields=["name"], name="idx_measurement_name"),
            models.Index(fields=["unit"], name="idx_measurement_unit"),
            models.Index(fields=["created_at"], name="idx_measurement_created"),
        ]

        verbose_name = _("Measurement Type")
        verbose_name_plural = _("Measurement Types")

    def __str__(self):
        return f"{self.name}"



    
class Observation(BaseTimeStamps):
   
    basin = models.ForeignKey(
        "basin.Basin",
        on_delete=models.CASCADE,
        related_name="observations",
        verbose_name=_("Basin"),
    )

    measurement_type = models.ForeignKey(
        MeasurementType,
        on_delete=models.CASCADE,
        related_name="observations",
        verbose_name=_("Measurement Type"),
    )

    timestamp = models.DateTimeField(
        _("Observation Timestamp"),
        db_index=True,
        help_text=_("Date and time of the observation"),
    )

    value = models.FloatField(
        _("Value"),
        help_text=_("Observed measurement value"),
    )

    source = models.CharField(
        _("Source"),
        max_length=100,
        default="CSV_Ingest",
        help_text=_("Source of the observation data"),
    )

    created_by = models.ForeignKey(
        "users.Users",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_observations",
    )

    updated_by = models.ForeignKey(
        "users.Users",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_observations",
    )

    class Meta:
        db_table = "observations"
        ordering = ("-id",)

        indexes = [
            models.Index(
                fields=["basin", "measurement_type", "timestamp"],
                name="idx_obs_basin_type_time",
            ),
            models.Index(
                fields=["timestamp"],
                name="idx_obs_timestamp",
            ),
            models.Index(
                fields=["created_at"],
                name="idx_obs_created",
            ),
        ]

        verbose_name = _("Observation")
        verbose_name_plural = _("Observations")

    def __str__(self):
        return (
            f"{self.basin.basin_id} | "
            f"{self.measurement_type.name} | "
        )