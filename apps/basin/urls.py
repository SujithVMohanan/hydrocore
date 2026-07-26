from django.urls import path

from apps.basin.api.views import (
    CreateOrUpdateBasinApiView,
    DeleteBasinsApiView,
    GetBasinsApiView,
)

urlpatterns = [


    # API Endpoints for Basin Management
    path('get-basins/', GetBasinsApiView.as_view(), name='basin-list'),
    path('create-or-update-basin/', CreateOrUpdateBasinApiView.as_view(), name='basin-create-or-update'),
    path('delete/', DeleteBasinsApiView.as_view(), name='basin-delete'),

]