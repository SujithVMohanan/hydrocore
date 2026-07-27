from rest_framework import serializers

from apps.observations.models import MeasurementType, Observation


class MeasurementTypeSchema(serializers.ModelSerializer):
    created_by = serializers.CharField(source='created_by.full_name', allow_null=True, read_only=True)
    updated_by = serializers.CharField(source='updated_by.full_name', allow_null=True, read_only=True)

    class Meta:
        model = MeasurementType
        fields = [
            'id',
            'name',
            'unit',
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


class ObservationListSchema(serializers.ModelSerializer):
    
    basin_id              = serializers.CharField(source='basin.basin_id', read_only=True)
    basin_name            = serializers.CharField(source='basin.name', read_only=True)
    measurement_type_id   = serializers.IntegerField(source='measurement_type.id', read_only=True)
    measurement_type_name = serializers.CharField(source='measurement_type.name', read_only=True)
    measurement_type_unit = serializers.CharField(source='measurement_type.unit', read_only=True)
    created_by            = serializers.CharField(source='created_by.full_name', allow_null=True, read_only=True)
    updated_by            = serializers.CharField(source='updated_by.full_name', allow_null=True, read_only=True)

    class Meta:
        model = Observation
        fields = [
            'id',
            'basin_id',
            'basin_name',
            'measurement_type_id',
            'measurement_type_name',
            'measurement_type_unit',
            'timestamp',
            'value',
            'source',
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
