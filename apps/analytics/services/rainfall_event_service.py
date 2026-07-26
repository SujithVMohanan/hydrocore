from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.observations.models import Observation, MeasurementType
from apps.analytics.models import RainfallEvent
from apps.basin.models import Basin
from utils.cache import CacheManager


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

        def fetch_data():
            return list(RainfallEvent.objects.select_related(
                "basin",
                "created_by",
                "updated_by",
            ).filter(filter_queryset).order_by("-id"))
            
        key = f"basin:{basin_id}:events:{min_dry_gap_used}:{start_timestamp}:{end_timestamp}:{search_query}:{unique_id}"
        data, _ = CacheManager.get_or_set(key, fetch_data, timeout=3600)
        return data

    @staticmethod
    @transaction.atomic
    def delete_rainfall_events(event_ids: list):
        if not event_ids:
            raise ValueError("Rainfall event IDs list cannot be empty.")

        deleted_count, _ = RainfallEvent.objects.filter(id__in=event_ids).delete()
        return deleted_count

    @staticmethod
    def get_timeseries(basin_id: int, measurement_type_id: int, start_timestamp=None, end_timestamp=None):
        def fetch_data():
            filter_q = Q(basin_id=basin_id, measurement_type_id=measurement_type_id)
            if start_timestamp:
                filter_q &= Q(timestamp__gte=start_timestamp)
            if end_timestamp:
                filter_q &= Q(timestamp__lte=end_timestamp)
    
            qs = Observation.objects.filter(filter_q).order_by("timestamp").select_related("measurement_type")
    
            hour_map = {}
            first_ts = None
            last_ts = None
            for obs in qs:
                ts = obs.timestamp.replace(minute=0, second=0, microsecond=0)
                if first_ts is None or ts < first_ts:
                    first_ts = ts
                if last_ts is None or ts > last_ts:
                    last_ts = ts
                hour_map[ts] = hour_map.get(ts, 0.0) + (obs.value or 0.0)
    
            if first_ts is None:
                return []
    
            start = start_timestamp or first_ts
            end = end_timestamp or last_ts
            start = start.replace(minute=0, second=0, microsecond=0)
            end = end.replace(minute=0, second=0, microsecond=0)
    
            events = list(RainfallEvent.objects.filter(basin_id=basin_id, start_timestamp__lte=end, end_timestamp__gte=start).values("id", "start_timestamp", "end_timestamp"))
    
            results = []
            cur = start
            measurement_unit = None
            try:
                mt = MeasurementType.objects.filter(id=measurement_type_id).first()
                if mt:
                    measurement_unit = mt.unit
            except Exception:
                measurement_unit = None
    
            while cur <= end:
                val = hour_map.get(cur, 0.0)
                event_id = None
                for ev in events:
                    if ev["start_timestamp"] <= cur <= ev["end_timestamp"]:
                        event_id = ev["id"]
                        break
    
                results.append({
                    "timestamp": cur,
                    "value": val,
                    "unit": measurement_unit or "",
                    "rainfall_event_id": event_id,
                })
                cur = cur + timezone.timedelta(hours=1)
    
            return results

        key = f"basin:{basin_id}:timeseries:{measurement_type_id}:{start_timestamp}:{end_timestamp}"
        data, _ = CacheManager.get_or_set(key, fetch_data, timeout=3600)
        return data

    @staticmethod
    @transaction.atomic
    def detect_and_persist_events(basin_id: int, min_dry_gap_hours: int, measurement_type_id: int, created_by=None, start_timestamp=None, end_timestamp=None):
        if min_dry_gap_hours is None or min_dry_gap_hours < 1:
            raise ValueError("min_dry_gap_hours must be a positive integer")

        # load observations aggregated by hour
        filter_q = Q(basin_id=basin_id, measurement_type_id=measurement_type_id)
        if start_timestamp:
            filter_q &= Q(timestamp__gte=start_timestamp)
        if end_timestamp:
            filter_q &= Q(timestamp__lte=end_timestamp)

        qs = Observation.objects.filter(filter_q).order_by("timestamp")

        hour_map = {}
        first_ts = None
        last_ts = None
        for obs in qs:
            ts = obs.timestamp.replace(minute=0, second=0, microsecond=0)
            if first_ts is None or ts < first_ts:
                first_ts = ts
            if last_ts is None or ts > last_ts:
                last_ts = ts
            hour_map[ts] = hour_map.get(ts, 0.0) + (obs.value or 0.0)

        if first_ts is None:
            return {"total_events": 0, "scanned_from": None, "scanned_to": None, "min_dry_gap_hours": min_dry_gap_hours}

        start = start_timestamp or first_ts
        end = end_timestamp or last_ts
        start = start.replace(minute=0, second=0, microsecond=0)
        end = end.replace(minute=0, second=0, microsecond=0)

        # state machine
        events_to_create = []
        current_start = None
        last_non_zero = None
        total_volume = 0.0
        peak_value = 0.0
        dry_streak = 0

        cur = start
        while cur <= end:
            val = hour_map.get(cur, 0.0)
            if val > 0:
                if current_start is None:
                    current_start = cur
                    total_volume = 0.0
                    peak_value = 0.0
                    dry_streak = 0
                total_volume += val
                if val > peak_value:
                    peak_value = val
                last_non_zero = cur
                dry_streak = 0
            else:
                if current_start is not None:
                    dry_streak += 1
                    if dry_streak >= min_dry_gap_hours:
                        # close event at last_non_zero
                        end_ts = last_non_zero
                        duration_hours = int((end_ts - current_start).total_seconds() / 3600) + 1
                        events_to_create.append(RainfallEvent(
                            basin_id=basin_id,
                            start_timestamp=current_start,
                            end_timestamp=end_ts,
                            duration_hours=duration_hours,
                            peak_value=peak_value,
                            total_volume=total_volume,
                            min_dry_gap_used=min_dry_gap_hours,
                            is_cold_event=False,
                            created_by=created_by,
                        ))
                        current_start = None
                        last_non_zero = None
                        total_volume = 0.0
                        peak_value = 0.0
                        dry_streak = 0
            cur = cur + timezone.timedelta(hours=1)

        # close lingering event
        if current_start is not None and last_non_zero is not None:
            end_ts = last_non_zero
            duration_hours = int((end_ts - current_start).total_seconds() / 3600) + 1
            events_to_create.append(RainfallEvent(
                basin_id=basin_id,
                start_timestamp=current_start,
                end_timestamp=end_ts,
                duration_hours=duration_hours,
                peak_value=peak_value,
                total_volume=total_volume,
                min_dry_gap_used=min_dry_gap_hours,
                is_cold_event=False,
                created_by=created_by,
            ))

        # delete existing events for basin+gap (idempotency)
        RainfallEvent.objects.filter(basin_id=basin_id, min_dry_gap_used=min_dry_gap_hours).delete()

        if events_to_create:
            RainfallEvent.objects.bulk_create(events_to_create)

        CacheManager.invalidate_basin_cache(basin_id)

        return {"total_events": len(events_to_create), "scanned_from": start, "scanned_to": end, "min_dry_gap_hours": min_dry_gap_hours}
