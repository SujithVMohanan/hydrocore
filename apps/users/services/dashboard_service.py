from typing import Dict, Any, Optional

from apps.basin.models import Basin
from apps.observations.models import MeasurementType
from apps.analytics.models import RainfallEvent
from apps.analytics.services.rainfall_event_service import RainfallEventService
from django.db.models import Avg, Max, Count


class DashboardService:

    @staticmethod
    def _parse_filter_date(value: Optional[str], *, end_of_day: bool = False):
        if not value:
            return None
        return RainfallEventService._coerce_datetime(value, end_of_day=end_of_day)

    @staticmethod
    def get_basins():
        return list(Basin.objects.values('id', 'basin_id', 'name').order_by('-id'))

    @staticmethod
    def get_dashboard_data(basin_id: int, start_date: str, end_date: str, min_dry_gap_hours: int = 6) -> Dict[str, Any]:
        
        if not basin_id:
            return {}

        start_dt = DashboardService._parse_filter_date(start_date)
        end_dt = DashboardService._parse_filter_date(end_date, end_of_day=True)

        measurement_types = {
            mt.name.lower(): mt
            for mt in MeasurementType.objects.filter(name__in=["Rainfall", "Temperature"])
        }
        rainfall_mt = measurement_types.get("rainfall")
        temp_mt     = measurement_types.get("temperature")

        rainfall_timeseries = []
        temp_timeseries = []
        events_list = []
        summary = {
            "total_events": 0,
            "mean_duration": 0.0,
            "highest_peak": 0.0
        }

        if rainfall_mt:

            RainfallEventService.detect_and_persist_events(
                basin_id=basin_id,
                min_dry_gap_hours=min_dry_gap_hours,
                measurement_type_id=rainfall_mt.id,
                start_timestamp=start_dt,
                end_timestamp=end_dt,
            )

            rainfall_timeseries = RainfallEventService.get_timeseries(
                basin_id=basin_id,
                measurement_type_id=rainfall_mt.id,
                start_timestamp=start_dt,
                end_timestamp=end_dt,
            )

            events_qs = RainfallEvent.objects.filter(
                basin_id=basin_id, 
                min_dry_gap_used=min_dry_gap_hours
            )
            
            if start_dt:
                events_qs = events_qs.filter(start_timestamp__gte=start_dt)
            if end_dt:
                events_qs = events_qs.filter(end_timestamp__lte=end_dt)
                
            events_qs = events_qs.order_by('-start_timestamp')
            
            events_list = list(events_qs.values(
                'id', 'start_timestamp', 'end_timestamp', 'duration_hours',
                'peak_value', 'total_volume', 'is_cold_event',
            ))

            for ev in events_list:
                ev['start_timestamp'] = ev['start_timestamp'].isoformat() if ev['start_timestamp'] else None
                ev['end_timestamp'] = ev['end_timestamp'].isoformat() if ev['end_timestamp'] else None

            stats = events_qs.aggregate(
                total_events=Count('id'),
                mean_duration=Avg('duration_hours'),
                highest_peak=Max('peak_value')
            )
            summary = {
                "total_events": stats['total_events'] or 0,
                "mean_duration": round(stats['mean_duration'] or 0.0, 1),
                "highest_peak": round(stats['highest_peak'] or 0.0, 2)
            }

        if temp_mt:
            temp_timeseries = RainfallEventService.get_timeseries(
                basin_id=basin_id,
                measurement_type_id=temp_mt.id,
                start_timestamp=start_dt,
                end_timestamp=end_dt,
            )

        for pt in rainfall_timeseries:
            pt['timestamp'] = pt['timestamp'].isoformat() if pt.get('timestamp') else None
            
        for pt in temp_timeseries:
            pt['timestamp'] = pt['timestamp'].isoformat() if pt.get('timestamp') else None

        return {
            "rainfall_timeseries": rainfall_timeseries,
            "temperature_timeseries": temp_timeseries,
            "events": events_list,
            "summary": summary
        }
