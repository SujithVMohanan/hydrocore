from rest_framework import serializers
from apps.basin.models import Basin


class BasinResponseSchemas(serializers.ModelSerializer):

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
        datas = super().to_representation(instance)
        for key in datas.keys():
            try:
                if datas[key] is None:
                    datas[key] = ""
            except KeyError:
                pass
        return datas