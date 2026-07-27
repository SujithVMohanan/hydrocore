from django.urls import path

from apps.basin.api.views import (
    CreateOrUpdateBasinApiView,
    DeleteBasinsApiView,
    GetBasinsApiView,
)
from apps.analytics.api.views import (
    BasinEventSummaryApiView,
    DetectRainfallEventsApiView,
    EventComparisonApiView,
    GetRainfallEventsApiView,
    GetTimeseriesApiView,
)

urlpatterns = [


    # API Endpoints for Basin Management
    path('get-basins/', GetBasinsApiView.as_view(), name='basin-list'),
    path('create-or-update-basin/', CreateOrUpdateBasinApiView.as_view(), name='basin-create-or-update'),
    path('delete/', DeleteBasinsApiView.as_view(), name='basin-delete'),
    path('<int:basin_id>/timeseries/', GetTimeseriesApiView.as_view(), name='basin-timeseries-pdf'),
    path('<int:basin_id>/events/', GetRainfallEventsApiView.as_view(), name='basin-event-list-pdf'),
    path('<int:basin_id>/detect-events/', DetectRainfallEventsApiView.as_view(), name='basin-detect-events-pdf'),
    path('<int:basin_id>/event-summary/', BasinEventSummaryApiView.as_view(), name='basin-event-summary-pdf'),
    path('<int:basin_id>/event-comparison/', EventComparisonApiView.as_view(), name='basin-event-comparison-pdf'),

]