from django.db import transaction
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist

from apps.basin.models import Basin
from apps.users.models import Users
from apps.observations.models import (
    MeasurementType, 
    Observation
)
from utils.cache import CacheManager


class ObservationService:

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
    def _resolve_basin(basin_id: int | str, required: bool = True) -> Basin | None:
        if basin_id is None:
            if required:
                raise ValueError("basin_id is required.")
            return None

        if isinstance(basin_id, str):
            basin_id = basin_id.strip()
            if not basin_id:
                if required:
                    raise ValueError("basin_id is required.")
                return None

            if not basin_id.isdigit():
                raise ValueError("basin_id must be an integer.")
            basin_id = int(basin_id)

        try:
            return Basin.objects.get(id=basin_id)
        except ObjectDoesNotExist:
            raise ValueError("Basin not found for the provided basin_id.")

    @staticmethod
    def _resolve_measurement_type(measurement_type_id: int, required: bool = True) -> MeasurementType | None:
        if measurement_type_id is None:
            if required:
                raise ValueError("measurement_type_id is required.")
            return None

        try:
            return MeasurementType.objects.get(id=measurement_type_id)
        except ObjectDoesNotExist:
            raise ValueError("Measurement type not found for the provided measurement_type_id.")

    @staticmethod
    def _prepare_observation_data(validated_data: dict, require_basin: bool = True, require_measurement_type: bool = True) -> dict:
        data                  = validated_data.copy()
        basin_id              = data.pop('basin_id', None)
        measurement_type_id   = data.pop('measurement_type_id', None)

        basin                 = ObservationService._resolve_basin(basin_id, required=require_basin)
        measurement_type = ObservationService._resolve_measurement_type(
            measurement_type_id,
            required=require_measurement_type,
        )

        if basin is not None:
            data['basin'] = basin
        if measurement_type is not None:
            data['measurement_type'] = measurement_type

        return data

    @staticmethod
    def get_observations(
        search_query: str = None,
        basin_id: str = None,
        measurement_type_id: int = None,
        start_timestamp: str = None,
        end_timestamp: str = None,
        value_above: float = None,
        value_below: float = None,
        unique_id: int = None,
    ):
        filter_queryset = Q()

        if search_query:
            query = search_query.strip()
            filter_queryset = (
                Q(basin__basin_id__icontains=query)
                | Q(measurement_type__name__icontains=query)
                | Q(source__icontains=query)
            )

        if basin_id:
            filter_queryset &= Q(basin__basin_id__iexact=basin_id.strip())

        if measurement_type_id:
            filter_queryset &= Q(measurement_type_id=measurement_type_id)

        if start_timestamp:
            filter_queryset &= Q(timestamp__gte=start_timestamp)

        if end_timestamp:
            filter_queryset &= Q(timestamp__lte=end_timestamp)

        if value_above is not None:
            filter_queryset &= Q(value__gte=value_above)

        if value_below is not None:
            filter_queryset &= Q(value__lte=value_below)

        if unique_id:
            filter_queryset &= Q(id=unique_id)

        return Observation.objects.select_related(
            "basin",
            "measurement_type",
            "created_by",
            "updated_by",
        ).filter(filter_queryset).order_by("-id")


    @staticmethod
    @transaction.atomic
    def create_observation(validated_data: dict, created_by=None) -> Observation:
        data = ObservationService._prepare_observation_data(validated_data, require_basin=True, require_measurement_type=True)
        observation = Observation.objects.create(
            created_by=ObservationService._resolve_user(created_by),
            **data
        )
        if observation.basin_id:
            CacheManager.invalidate_basin_cache(observation.basin_id)
        return observation


    @staticmethod
    @transaction.atomic
    def update_observation(observation_id: int, validated_data: dict, updated_by=None) -> Observation:
        data = ObservationService._prepare_observation_data(validated_data, require_basin=False, require_measurement_type=False)
        observation = Observation.objects.get(id=observation_id)
        for field, value in data.items():
            setattr(observation, field, value)

        observation.updated_by = ObservationService._resolve_user(updated_by)
        observation.save()
        if observation.basin_id:
            CacheManager.invalidate_basin_cache(observation.basin_id)
        return observation


    @staticmethod
    def delete_observations(observation_ids: list):
        if not observation_ids:
            raise ValueError("Observation IDs list cannot be empty.")

        deleted_count, _ = Observation.objects.filter(id__in=observation_ids).delete()
        return deleted_count
