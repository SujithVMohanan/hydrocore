from rest_framework import serializers


class IntegerListField(serializers.Field):
    def to_internal_value(self, data):
        try:
            if isinstance(data, list):
                return [int(v) for v in data]
            return [int(v) for v in str(data).split(",") if v.strip()]
        except (ValueError, TypeError):
            raise serializers.ValidationError("Must be a list of integers or a comma-separated string.")

    def to_representation(self, value):
        return ",".join(str(val) for val in value)
    

    