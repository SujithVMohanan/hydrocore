from django.urls import path

from apps.analytics.api.views import (
    GetRainfallEventsApiView,
    DeleteRainfallEventsApiView,
)

urlpatterns = [

    # API Endpoints for Rainfall Event Management
    path('get-rainfall-events/', GetRainfallEventsApiView.as_view(), name='rainfall-event-list'),
    path('delete-rainfall-events/', DeleteRainfallEventsApiView.as_view(), name='rainfall-event-delete'),
]