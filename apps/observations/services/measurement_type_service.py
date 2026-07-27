from django.db import transaction
from django.db.models import Q

from apps.users.models import Users
from apps.observations.models import MeasurementType


class MeasurementTypeService:

    @staticmethod
    def _resolve_user(user) -> 'Users | None':
        if user is None:
            return None
        if isinstance(user, Users):
            return user

        user_id = getattr(user, 'id', None)
        if user_id:
            return Users.objects.filter(id=user_id).first()
        return None

    @staticmethod
    def get_measurement_types(search_query: str = None, name: str = None, unit: str = None, unique_id: int = None):
        filter_queryset = Q()

        if search_query:
            query = search_query.strip()
            filter_queryset = Q(name__icontains=query) | Q(unit__icontains=query)

        if name:
            filter_queryset &= Q(name__iexact=name.strip())

        if unit:
            filter_queryset &= Q(unit__iexact=unit.strip())

        if unique_id:
            filter_queryset &= Q(id=unique_id)

        return MeasurementType.objects.filter(filter_queryset).order_by("-id")

    @staticmethod
    @transaction.atomic
    def create_measurement_type(validated_data: dict, created_by=None) -> MeasurementType:
        data = validated_data.copy()
        measurement_type = MeasurementType.objects.create(
            created_by=MeasurementTypeService._resolve_user(created_by),
            **data
        )
        return measurement_type

    @staticmethod
    @transaction.atomic
    def update_measurement_type(measurement_type_id: int, validated_data: dict, updated_by=None) -> MeasurementType:
        measurement_type = MeasurementType.objects.get(id=measurement_type_id)
        for field, value in validated_data.items():
            setattr(measurement_type, field, value)

        measurement_type.updated_by = MeasurementTypeService._resolve_user(updated_by)
        measurement_type.save()
        return measurement_type

    @staticmethod
    def delete_measurement_types(measurement_type_ids: list):
        if not measurement_type_ids:
            raise ValueError("Measurement type IDs list cannot be empty.")

        deleted_count, _ = MeasurementType.objects.filter(id__in=measurement_type_ids).delete()
        return deleted_count
