"""
URL configuration for hydrocore project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import (
    path, 
    re_path, 
    include
)
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic import RedirectView

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from hydrocore.settings import BASE_DIR


schema_view = get_schema_view(
    openapi.Info(
        title="Hydrocore API",
        default_version='v1',
        description="Comprehensive API documentation for Hydrocore platform",
        terms_of_service="",
        contact=openapi.Contact(email="sujithvaderiyattil@gmail.com"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('apps.users.urls')),

    path('', RedirectView.as_view(url='api/docs/')),


    # API Endpoints 
    re_path(r'^api/', include([

        path('users/', include('apps.users.urls')),
        path('basin/', include('apps.basin.urls')),
        path('observations/', include('apps.observations.urls')),
        path('analytics/', include('apps.analytics.urls')),
        
        
        re_path(r'^docs/', include([
            path('', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
            path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
            path('json/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
        ])),
    ])),
]




if settings.DEBUG:

    urlpatterns += staticfiles_urlpatterns()

    urlpatterns += static(settings.STATIC_URL, document_root=BASE_DIR / "static")
    
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )