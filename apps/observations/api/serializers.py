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


class IngestObservationsSerializer(serializers.Serializer):
    rainfall_file = serializers.FileField(required=False, allow_empty_file=False)
    temperature_file = serializers.FileField(required=False, allow_empty_file=False)
    auto_create_basins = serializers.BooleanField(required=False, default=True)

    MAX_CSV_BYTES = 200 * 1024 * 1024  # 200 MB

    def validate_rainfall_file(self, value):
        return self._validate_csv_file(value, 'rainfall')

    def validate_temperature_file(self, value):
        return self._validate_csv_file(value, 'temperature')

    def _validate_csv_file(self, uploaded_file, label: str):
        if not uploaded_file.name.lower().endswith('.csv'):
            raise serializers.ValidationError(f'{label} file must be a .csv file.')
        if uploaded_file.size > self.MAX_CSV_BYTES:
            raise serializers.ValidationError(
                f'{label} file exceeds maximum size of {self.MAX_CSV_BYTES // (1024 * 1024)} MB.'
            )
        return uploaded_file

    def validate(self, attrs):
        if not attrs.get('rainfall_file') and not attrs.get('temperature_file'):
            raise serializers.ValidationError(
                'At least one of rainfall_file or temperature_file is required.'
            )
        return attrs
