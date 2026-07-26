from django.urls import path

from apps.analytics.api.views import (
    DetectRainfallEventsApiView,
    GetRainfallEventsApiView,
    DeleteRainfallEventsApiView,
    GetTimeseriesApiView,
)

urlpatterns = [

    # API Endpoints for Rainfall Event Management
    path('get-rainfall-events/', GetRainfallEventsApiView.as_view(), name='rainfall-event-list'),
    path('delete-rainfall-events/', DeleteRainfallEventsApiView.as_view(), name='rainfall-event-delete'),
    path('basins/<int:basin_id>/timeseries/', GetTimeseriesApiView.as_view(), name='basin-timeseries'),
    path('basins/<int:basin_id>/detect-events/', DetectRainfallEventsApiView.as_view(), name='basin-detect-events'),
]