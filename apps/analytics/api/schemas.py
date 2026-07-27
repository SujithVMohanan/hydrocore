from rest_framework import serializers

from apps.analytics.models import RainfallEvent


class RainfallEventSchema(serializers.ModelSerializer):

    basin_id = serializers.CharField(source='basin.basin_id', read_only=True)
    basin_name = serializers.CharField(source='basin.name', read_only=True)
    created_by = serializers.CharField(source='created_by.full_name', allow_null=True, read_only=True)
    updated_by = serializers.CharField(source='updated_by.full_name', allow_null=True, read_only=True)

    class Meta:
        model = RainfallEvent
        fields = [
            'id',
            'basin_id',
            'basin_name',
            'start_timestamp',
            'end_timestamp',
            'duration_hours',
            'peak_value',
            'total_volume',
            'min_dry_gap_used',
            'is_cold_event',
            'detected_at',
            'created_by',
            'updated_by',
            'created_at',
            'updated_at',
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for key, value in data.items():
            if value is None:
                data[key] = ""
        return data


class TimeseriesPointSchema(serializers.Serializer):

    timestamp           = serializers.DateTimeField()
    value               = serializers.FloatField()
    unit                = serializers.CharField(allow_blank=True)
    rainfall_event_id   = serializers.IntegerField(allow_null=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for key, value in data.items():
            if value is None:
                data[key] = ""
        return data


class EventSummaryEventSchema(serializers.Serializer):

    id                = serializers.IntegerField()
    start_timestamp   = serializers.DateTimeField()
    end_timestamp     = serializers.DateTimeField()
    duration_hours    = serializers.IntegerField()
    peak_value        = serializers.FloatField()
    total_volume      = serializers.FloatField()
    min_dry_gap_used  = serializers.IntegerField()
    is_cold_event     = serializers.BooleanField()
    detected_at       = serializers.DateTimeField(allow_null=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for key, value in data.items():
            if value is None:
                data[key] = ""
        return data


class EventSummarySchema(serializers.Serializer):

    basin_id            = serializers.IntegerField()
    min_dry_gap_hours   = serializers.IntegerField(allow_null=True)
    total_events        = serializers.IntegerField()
    mean_duration       = serializers.FloatField()
    mean_total_volume   = serializers.FloatField()
    peak_event          = EventSummaryEventSchema(allow_null=True)
    longest_event       = EventSummaryEventSchema(allow_null=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for key, value in data.items():
            if value is None:
                data[key] = ""
        return data


class EventComparisonGapSchema(serializers.Serializer):

    min_dry_gap_hours   = serializers.IntegerField()
    total_events        = serializers.IntegerField()
    mean_duration       = serializers.FloatField()
    mean_total_volume   = serializers.FloatField()
    peak_event          = EventSummaryEventSchema(allow_null=True)
    longest_event       = EventSummaryEventSchema(allow_null=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for key, value in data.items():
            if value is None:
                data[key] = ""
        return data


class EventComparisonSchema(serializers.Serializer):
    
    basin_id    = serializers.IntegerField()
    comparisons = EventComparisonGapSchema(many=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for key, value in data.items():
            if value is None:
                data[key] = ""
        return data
