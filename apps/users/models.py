from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager
)
import uuid

class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):

        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)

        user = self.model(
            email=email,
            **extra_fields
        )

        user.set_password(password)

        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None, **extra_fields):

        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True")

        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(email, password, **extra_fields)


class Users(AbstractBaseUser, PermissionsMixin):

    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True
    )

    full_name = models.CharField(_("Full Name"),
        max_length=255,
        blank=True,
        null=True
    )

    phone_number = models.CharField(_("Phone Number"),
        max_length=20,
        unique=True,
        blank=True,
        null=True
    )

    email = models.EmailField(_("Email Address"),
        max_length=255,
        unique=True
    )

    profile_image = models.FileField(_("Profile Image"),
        upload_to='users/profile/',
        blank=True,
        null=True
    )

    
    is_active = models.BooleanField(_("Is Active"), default=True)
    is_staff  = models.BooleanField(_("Is Staff"), default=False)

    
    
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    created_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='created_users'
    )

    updated_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='updated_users'
    )

  
    objects = UserManager()

    USERNAME_FIELD = 'email'

    REQUIRED_FIELDS = [

    ]

    
    class Meta:
        ordering = ['id']

        verbose_name = _('user')
        verbose_name_plural = _('users')

        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone_number']),
        ]


    def __str__(self):
        return f"{self.email}"
    

