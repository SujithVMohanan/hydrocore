from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.users.models import (
    BaseTimeStamps
)


class RainfallEvent(BaseTimeStamps):

    basin            = models.ForeignKey("basin.Basin", on_delete=models.CASCADE, related_name="rainfall_events", verbose_name=_("Basin"))
    start_timestamp  = models.DateTimeField(_("Start Time"), help_text=_("Rainfall event start time"))
    end_timestamp    = models.DateTimeField(_("End Time"), help_text=_("Rainfall event end time"))
    duration_hours   = models.PositiveIntegerField(_("Duration (Hours)"), help_text=_("Total duration of the rainfall event in hours"))
    peak_value       = models.FloatField(_("Peak Rainfall"), help_text=_("Maximum rainfall intensity (mm/hr)"))
    total_volume     = models.FloatField(_("Total Rainfall"), help_text=_("Total cumulative rainfall (mm)"))
    min_dry_gap_used = models.PositiveSmallIntegerField(_("Minimum Dry Gap"), help_text=_("Dry gap parameter used (hours)"))
    is_cold_event    = models.BooleanField(_("Cold Event"), default=False, help_text=_("True if mean temperature is below 0°C"))

    created_by       = models.ForeignKey("users.Users", on_delete=models.SET_NULL, null=True, blank=True, related_name="rainfall_events_created")
    updated_by       = models.ForeignKey("users.Users", on_delete=models.SET_NULL, null=True, blank=True, related_name="rainfall_events_updated")

    class Meta:
        db_table = "rainfall_events"
        ordering = ("-id",)

        constraints = [
            models.UniqueConstraint(
                fields=["basin", "start_timestamp", "min_dry_gap_used"],
                name="uq_event_basin_start_gap",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "basin",
                    "min_dry_gap_used",
                    "start_timestamp",
                ],
                name="idx_event_lookup",
            ),
            models.Index(
                fields=["start_timestamp"],
                name="idx_event_start",
            ),
            models.Index(
                fields=["end_timestamp"],
                name="idx_event_end",
            ),
            models.Index(
                fields=["created_at"],
                name="idx_event_created",
            ),
        ]

        verbose_name = _("Rainfall Event")
        verbose_name_plural = _("Rainfall Events")

    def __str__(self):
        return (
            f"{self.basin.basin_id} | "
            f"{self.start_timestamp:%Y-%m-%d %H:%M} "
        )