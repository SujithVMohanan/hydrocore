from django.db import transaction
from django.db.models import Q

from apps.basin.models import Basin
from apps.users.models import Users
from utils.cache import CacheManager


class BasinService:

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
    def get_basins(search_query: str = None, basin_id: str = None, name: str = None, unique_id: int = None):
        filter_queryset = Q()

        if search_query:
            query = search_query.strip()
            filter_queryset = Q(basin_id__icontains=query) | Q(name__icontains=query)

        if basin_id:
            filter_queryset &= Q(basin_id__iexact=basin_id.strip())

        if name:
            filter_queryset &= Q(name__icontains=name.strip())

        if unique_id:
            filter_queryset &= Q(id=unique_id)

        def fetch_data():
            return list(Basin.objects.filter(filter_queryset).order_by("-id"))
            
        key = f"basin:list_or_summary:{search_query}:{basin_id}:{name}:{unique_id}"
        data, _ = CacheManager.get_or_set(key, fetch_data, timeout=3600)
        return data


    @staticmethod
    @transaction.atomic
    def create_basin(validated_data: dict, created_by=None) -> Basin:
        data = validated_data.copy()
        basin = Basin.objects.create(
            created_by=BasinService._resolve_user(created_by),
            **data
        )
        return basin



    @staticmethod
    @transaction.atomic
    def update_basin(basin_id: int, validated_data: dict, updated_by=None) -> Basin:
        basin = Basin.objects.get(id=basin_id)

        for field, value in validated_data.items():
            setattr(basin, field, value)

        basin.updated_by = BasinService._resolve_user(updated_by)
        basin.save()
        return basin


    @staticmethod
    def delete_basins(basin_ids: list):
        if not basin_ids:
            raise ValueError("Basin IDs list cannot be empty.")

        deleted_count, _ = Basin.objects.filter(id__in=basin_ids).delete()
        return deleted_count


