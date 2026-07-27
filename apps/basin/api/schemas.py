from rest_framework import serializers

from apps.basin.models import Basin


class BasinListSchema(serializers.ModelSerializer):
    created_by = serializers.CharField(source='created_by.full_name', allow_null=True, read_only=True)
    updated_by = serializers.CharField(source='updated_by.full_name', allow_null=True, read_only=True)

    class Meta:
        model = Basin
        fields = [
            'id',
            'basin_id',
            'name',
            'metadata',
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
