from rest_framework import serializers
from apps.users.models import Users


class GetUsersApiSchema(serializers.ModelSerializer):
    
    class Meta:
        model = Users
        fields = [
            'id',
            'uuid',
            'full_name',
            'email',
            'phone_number',
            'profile_image',
            'is_active',
            'is_staff',
            'created_at',
            'updated_at',
            'created_by',
            'updated_by',
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


class RegisterUserResponseSchema(serializers.ModelSerializer):
    
    class Meta:
        model = Users
        fields = [
            'full_name',
            'email',
            'phone_number',
            'profile_image',
            'is_active',
            'is_staff',
            'is_superuser',
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


class CreateOrUpdateUserResponseSchema(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = [
            'id',
            'uuid',
            'full_name',
            'email',
            'phone_number',
            'profile_image',
            'is_active',
            'is_staff',
            'created_at',
            'updated_at',
            'created_by',
            'updated_by',
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
