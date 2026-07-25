from django.db import transaction
from django.db.models import Q
from apps.users.models import Users


class UserService:

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
    def get_users(search_query: str = None, email: str = None, full_name: str = None, user_id: int = None):
        filter_queryset = Q()

        if search_query:
            query = search_query.strip()
            filter_queryset = (Q(full_name__icontains=query) | Q(email__icontains=query))

        if user_id:
            filter_queryset &= Q(id=user_id)

        if email:
            filter_queryset &= Q(email__iexact=email.strip())

        if full_name:
            filter_queryset &= Q(full_name__icontains=full_name.strip())

        return Users.objects.filter(
            filter_queryset
        ).exclude(is_superuser=True).order_by("-id")

    @staticmethod
    @transaction.atomic
    def register_user(validated_data: dict, created_by=None) -> Users:
        
        data     = validated_data.copy()
        password = data.pop('password')
        user = Users.objects.create_user(
            password=password,
            created_by=UserService._resolve_user(created_by),
            **data
        )
        return user

    @staticmethod
    def delete_users(user_ids: list):
        if not user_ids:
            raise ValueError("User IDs list cannot be empty.")

        deleted_count, _ = (
            Users.objects
            .filter(id__in=user_ids)
            .exclude(is_superuser=True)
            .delete()
        )

        return deleted_count

    @staticmethod
    @transaction.atomic
    def create_user(validated_data: dict, created_by=None) -> Users:
        
        data     = validated_data.copy()
        password = data.pop('password', None)

        user = Users.objects.create_user(
            password=password,
            created_by=UserService._resolve_user(created_by),
            **data
        )
        return user

    @staticmethod
    @transaction.atomic
    def update_user(user_id: int, validated_data: dict, updated_by=None) -> Users:
        
        user = Users.objects.get(id=user_id)

        password = validated_data.pop('password', None)

        for field, value in validated_data.items():
            setattr(user, field, value)

        if password:
            user.set_password(password)

        user.updated_by = UserService._resolve_user(updated_by)

        user.save()
        return user