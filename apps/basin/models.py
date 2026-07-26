from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.users.models import (
    BaseTimeStamps
)


class Basin(BaseTimeStamps):
    basin_id = models.CharField(
        _("Basin ID"),
        max_length=20,
        unique=True,
        db_index=True,
        editable=False,
        blank=True,
    )

    name = models.CharField(
        _("Basin Name"),
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        help_text="Optional basin name",
    )

    metadata = models.JSONField(
        _("Basin Metadata"),
        default=dict,
        blank=True,
        help_text="Additional basin information",
    )

    created_by = models.ForeignKey(
        "users.Users",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_basins",
    )

    updated_by = models.ForeignKey(
        "users.Users",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_basins",
    )

    class Meta:
        db_table = "basins"
        ordering = ("-id",)

        indexes = [
            models.Index(fields=["name"], name="idx_basin_name"),
            models.Index(fields=["created_at"], name="idx_basin_created"),
        ]

        verbose_name = _("Basin")
        verbose_name_plural = _("Basins")

    def save(self, *args, **kwargs):
        is_new = self._state.adding

        super().save(*args, **kwargs)

        if is_new and not self.basin_id:
            self.basin_id = f"BSN-{1000 + self.id}"
            super().save(update_fields=["basin_id"])

    def __str__(self):
        return f"{self.basin_id}"