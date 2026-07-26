from rest_framework import serializers

from apps.basin.models import Basin
from apps.observations.models import MeasurementType, Observation
from utils.integer_list_field import IntegerListField


class MeasurementTypeCreateUpdateSerializer(serializers.Serializer):
    id    = serializers.IntegerField(required=False, allow_null=True)
    name  = serializers.CharField(max_length=50, required=True)
    unit  = serializers.CharField(max_length=20, required=True)

    def validate_name(self, value):
        name = value.strip()
        qs = MeasurementType.objects.filter(name__iexact=name)
        if self.context.get('id'):
            qs = qs.exclude(id=self.context['id'])
        if qs.exists():
            raise serializers.ValidationError("A measurement type with this name already exists.")
        return name


class ObservationCreateUpdateSerializer(serializers.Serializer):
    id                    = serializers.IntegerField(required=False, allow_null=True)
    basin_id              = serializers.IntegerField(required=True, help_text="Unique basin primary key ID")
    measurement_type_id   = serializers.IntegerField(required=True)
    timestamp             = serializers.DateTimeField(required=True)
    value                 = serializers.FloatField(required=True)
    source                = serializers.CharField(max_length=100, required=False, allow_blank=True, default="CSV_Ingest")

    def validate_basin_id(self, value):
        if not Basin.objects.filter(id=value).exists():
            raise serializers.ValidationError("Basin not found for the provided basin_id.")
        return value

    def validate_measurement_type_id(self, value):
        if not MeasurementType.objects.filter(id=value).exists():
            raise serializers.ValidationError("Measurement type not found for the provided measurement_type_id.")
        return value


class ObservationDeleteSerializer(serializers.Serializer):
    ids = IntegerListField(required=True, help_text="Comma-separated observation IDs, for example: 1,2,3")


class MeasurementTypeDeleteSerializer(serializers.Serializer):
    ids = IntegerListField(required=True, help_text="Comma-separated measurement type IDs, for example: 1,2,3")
