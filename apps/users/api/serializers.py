from django.contrib.auth import authenticate
from rest_framework import serializers
from apps.users.models import Users
from utils.integer_list_field import IntegerListField


class RegisterUserSerializer(serializers.Serializer):

    full_name       = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    email           = serializers.EmailField(required=True)
    phone_number    = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)
    password        = serializers.CharField(write_only=True, required=True, min_length=8)
    profile_image   = serializers.FileField(required=False, allow_null=True)


    def validate_email(self, value):
        normalized_email = value.strip().lower()
        if Users.objects.filter(email__iexact=normalized_email).exists():
            raise serializers.ValidationError("A user with this email address already exists.")
        return normalized_email

    def validate_phone_number(self, value):
        if value:
            phone = value.strip()
            if Users.objects.filter(phone_number=phone).exists():
                raise serializers.ValidationError("A user with this phone number already exists.")
            return phone
        return value


class LoginUserSerializer(serializers.Serializer):

    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        user = authenticate(request=self.context.get('request'), email=email, password=password)

        if not user:
            raise serializers.ValidationError({"detail": "Invalid email or password."})

        attrs['user'] = user
        return attrs



class UserDeleteSerializer(serializers.Serializer):

    user_ids = IntegerListField(required=True)


class CreateOrUpdateUserSerializer(serializers.Serializer):

    user_id        = serializers.PrimaryKeyRelatedField(required=False, queryset=Users.objects.all())
    full_name       = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    email           = serializers.EmailField(required=False)
    phone_number    = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)
    password        = serializers.CharField(write_only=True, required=False, min_length=8, allow_null=True)
    profile_image   = serializers.FileField(required=False, allow_null=True)
    is_active       = serializers.BooleanField(required=False)
    is_staff        = serializers.BooleanField(required=False)

    def _get_user_id(self):
        return self.context.get('user_id')

    def validate_email(self, value):
        normalized = value.strip().lower()
        user_id = self._get_user_id()
        qs      = Users.objects.filter(email__iexact=normalized)
        if user_id:
            qs = qs.exclude(id=user_id)
        if qs.exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return normalized

    def validate_phone_number(self, value):
        if value:
            phone = value.strip()
            user_id = self._get_user_id()
            qs = Users.objects.filter(phone_number=phone)
            if user_id:
                qs = qs.exclude(id=user_id)
            if qs.exists():
                raise serializers.ValidationError("A user with this phone number already exists.")
            return phone
        return value
