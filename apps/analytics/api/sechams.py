from rest_framework import serializers


class TimeseriesPointSchemas(serializers.Serializer):
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
