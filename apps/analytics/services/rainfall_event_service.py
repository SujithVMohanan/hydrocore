from django.db import transaction
from django.db.models import Q

from apps.analytics.models import RainfallEvent


class RainfallEventService:

    @staticmethod
    def get_rainfall_events(
        search_query: str = None,
        basin_id: int = None,
        start_timestamp: str = None,
        end_timestamp: str = None,
        min_dry_gap_used: int = None,
        unique_id: int = None,
    ):
        filter_queryset = Q()

        if search_query:
            query = search_query.strip()
            filter_queryset = (
                Q(basin__basin_id__icontains=query)
                | Q(peak_value__icontains=query)
                | Q(total_volume__icontains=query)
            )

        if basin_id:
            filter_queryset &= Q(basin_id=basin_id)

        if start_timestamp:
            filter_queryset &= Q(start_timestamp__gte=start_timestamp)

        if end_timestamp:
            filter_queryset &= Q(end_timestamp__lte=end_timestamp)

        if min_dry_gap_used:
            filter_queryset &= Q(min_dry_gap_used=min_dry_gap_used)

        if unique_id:
            filter_queryset &= Q(id=unique_id)

        return RainfallEvent.objects.select_related(
            "basin",
            "created_by",
            "updated_by",
        ).filter(filter_queryset).order_by("-id")

    @staticmethod
    @transaction.atomic
    def delete_rainfall_events(event_ids: list):
        if not event_ids:
            raise ValueError("Rainfall event IDs list cannot be empty.")

        deleted_count, _ = RainfallEvent.objects.filter(id__in=event_ids).delete()
        return deleted_count
