from rest_framework import serializers
from apps.basin.models import Basin
from utils.integer_list_field import IntegerListField


class BasinCreateUpdateSerializer(serializers.Serializer):

    id          = serializers.IntegerField(required=False, allow_null=True)
    basin_id    = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)
    name        = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    metadata    = serializers.JSONField(required=False, default=dict)

    def validate_basin_id(self, value):
        if value:
            value = value.strip()
            qs = Basin.objects.filter(basin_id__iexact=value)
            if self.context.get('id'):
                qs = qs.exclude(id=self.context['id'])
            if qs.exists():
                raise serializers.ValidationError("A basin with this basin_id already exists.")
            return value
        return value


class BasinDeleteSerializer(serializers.Serializer):

    ids = IntegerListField(required=True, help_text="Comma-separated basin IDs, for example: 1,2,3")
