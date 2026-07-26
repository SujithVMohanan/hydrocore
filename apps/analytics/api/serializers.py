from rest_framework import serializers
from utils.integer_list_field import IntegerListField
from apps.analytics.models import RainfallEvent


class RainfallEventResponseSchema(serializers.ModelSerializer):
    basin_id    = serializers.CharField(source='basin.basin_id', read_only=True)
    basin_name  = serializers.CharField(source='basin.name', read_only=True)
    created_by  = serializers.CharField(source='created_by.full_name', allow_null=True, read_only=True)
    updated_by  = serializers.CharField(source='updated_by.full_name', allow_null=True, read_only=True)

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


class RainfallEventDeleteSerializer(serializers.Serializer):
    ids = IntegerListField(required=True, help_text="Comma-separated rainfall event IDs, for example: 1,2,3")


class DetectEventsResponseSerializer(serializers.Serializer):
    total_events        = serializers.IntegerField()
    scanned_from        = serializers.DateTimeField(allow_null=True)
    scanned_to          = serializers.DateTimeField(allow_null=True)
    min_dry_gap_hours   = serializers.IntegerField()
