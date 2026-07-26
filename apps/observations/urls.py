from django.urls import path

from apps.observations.api.views import (
    CreateOrUpdateMeasurementTypeApiView,
    DeleteMeasurementTypesApiView,
    GetMeasurementTypesApiView,
    CreateOrUpdateObservationApiView,
    DeleteObservationsApiView,
    GetObservationsApiView,
)

urlpatterns = [

    # API Endpoints for Observation Management
    path('get-measurement-types/', GetMeasurementTypesApiView.as_view(), name='measurement-type-list'),
    path('create-or-update-measurement-type/', CreateOrUpdateMeasurementTypeApiView.as_view(), name='measurement-type-create-or-update'),
    path('delete-measurement-types/', DeleteMeasurementTypesApiView.as_view(), name='measurement-type-delete'),

    path('get-observations/', GetObservationsApiView.as_view(), name='observation-list'),
    path('create-or-update-observation/', CreateOrUpdateObservationApiView.as_view(), name='observation-create-or-update'),
    path('delete-observations/', DeleteObservationsApiView.as_view(), name='observation-delete'),
]