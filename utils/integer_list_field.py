from rest_framework import serializers


class IntegerListField(serializers.Field):
    def to_internal_value(self, data):
        try:
            return [int(value) for value in data.split(",")]
        except ValueError:
            raise serializers.ValidationError("Invalid value")

    def to_representation(self, value):
        return ",".join(str(val) for val in value)
    

    