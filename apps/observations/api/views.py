from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.response import Response
from django.db import transaction

from apps.observations.models import (
    MeasurementType, 
    Observation
)

from apps.observations.services.measurement_type_service import MeasurementTypeService
from apps.observations.services.observation_service import ObservationService
from apps.observations.services.ingestion_service import IngestionService
from apps.observations.services.ingestion_errors import IngestionError
from apps.observations.api.serializers import (
    MeasurementTypeCreateUpdateSerializer,
    ObservationCreateUpdateSerializer,
    ObservationDeleteSerializer,
    MeasurementTypeDeleteSerializer,
    IngestObservationsSerializer,
)
from apps.observations.api.sechams import (
    MeasurementTypeResponseSchema,
    ObservationResponseSchemas,
)
from utils.api_utils import (
    ResponseInfo,
    RestPagination
)

from utils.custom_exception import ExceptionHandler


class GetMeasurementTypesApiView(generics.ListAPIView):
    def __init__(self, **kwargs):
        self.response_format = ResponseInfo().response
        super(GetMeasurementTypesApiView, self).__init__(**kwargs)

    serializer_class   = MeasurementTypeResponseSchema
    permission_classes = [IsAuthenticated]
    pagination_class   = RestPagination

    search = openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                                description="Filter by measurement type name or unit")
    name = openapi.Parameter('name', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                                description="Exact measurement type name")
    unit = openapi.Parameter('unit', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                                description="Exact measurement type unit")
    id = openapi.Parameter('id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=False,
                                description="Single measurement type ID to fetch specific details")

    @swagger_auto_schema(tags=["Measurement Types"], manual_parameters=[search, name, unit, id], pagination_class=RestPagination)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, *args, **kwargs):
        return MeasurementTypeService.get_measurement_types(
            search_query=self.request.query_params.get('search'),
            name=self.request.query_params.get('name'),
            unit=self.request.query_params.get('unit'),
            unique_id=self.request.query_params.get('id'),
        )



class CreateOrUpdateMeasurementTypeApiView(generics.GenericAPIView):
    def __init__(self, **kwargs):
        self.response_format = ResponseInfo().response
        super(CreateOrUpdateMeasurementTypeApiView, self).__init__(**kwargs)

    serializer_class    = MeasurementTypeCreateUpdateSerializer
    response_schema     = MeasurementTypeResponseSchema
    permission_classes  = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Measurement Types"],
        request_body=MeasurementTypeCreateUpdateSerializer,
        responses={200: MeasurementTypeResponseSchema, 201: MeasurementTypeResponseSchema},
        operation_summary="Create or Update Measurement Type",
        operation_description=(
            "Pass `id` in the request body to update an existing measurement type."
            " Omit `id` (or pass null) to create a new measurement type."
        )
    )
    def post(self, request, *args, **kwargs):
        try:
            measurement_type_id = request.data.get('id') or None
            serializer = self.serializer_class(data=request.data, context={'id': measurement_type_id})
            if not serializer.is_valid():
                self.response_format['status_code'] = status.HTTP_400_BAD_REQUEST
                self.response_format['status'] = False
                self.response_format['errors'] = serializer.errors
                return Response(self.response_format, status=status.HTTP_400_BAD_REQUEST)

            data = serializer.validated_data.copy()
            data.pop('id', None)

            if measurement_type_id:
                try:
                    measurement_type = MeasurementTypeService.update_measurement_type(
                        measurement_type_id=int(measurement_type_id),
                        validated_data=data,
                        updated_by=request.user,
                    )
                except MeasurementType.DoesNotExist:
                    self.response_format['status_code'] = status.HTTP_404_NOT_FOUND
                    self.response_format['status'] = False
                    self.response_format['message'] = "Measurement type not found."
                    return Response(self.response_format, status=status.HTTP_404_NOT_FOUND)

                http_status = status.HTTP_200_OK
                message = "Measurement type updated successfully."
            else:
                measurement_type = MeasurementTypeService.create_measurement_type(
                    validated_data=data,
                    created_by=request.user,
                )
                http_status = status.HTTP_201_CREATED
                message = "Measurement type created successfully."

            self.response_format['status_code'] = http_status
            self.response_format['status'] = True
            self.response_format['message'] = message
            self.response_format['data'] = self.response_schema(measurement_type, context={'request': request}).data
            return Response(self.response_format, status=http_status)

        except Exception as e:
            return ExceptionHandler.handle(e)


class DeleteMeasurementTypesApiView(generics.DestroyAPIView):
    def __init__(self, **kwargs):
        self.response_format = ResponseInfo().response
        super(DeleteMeasurementTypesApiView, self).__init__(**kwargs)

    serializer_class = MeasurementTypeDeleteSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Measurement Types"],
        request_body=MeasurementTypeDeleteSerializer,
        operation_description="Pass measurement type IDs as a comma-separated string, for example: 1,2,3"
    )
    def delete(self, request, *args, **kwargs):
        try:
            serializer = self.serializer_class(data=request.data)
            if not serializer.is_valid():
                self.response_format['status_code'] = status.HTTP_400_BAD_REQUEST
                self.response_format['status'] = False
                self.response_format['errors'] = serializer.errors
                return Response(self.response_format, status=status.HTTP_400_BAD_REQUEST)

            measurement_type_ids = serializer.validated_data['ids']
            MeasurementTypeService.delete_measurement_types(measurement_type_ids=measurement_type_ids)

            self.response_format['status_code'] = status.HTTP_200_OK
            self.response_format['status'] = True
            self.response_format['message'] = "Measurement types deleted successfully."
            return Response(self.response_format, status=status.HTTP_200_OK)

        except Exception as e:
            return ExceptionHandler.handle(e)




class GetObservationsApiView(generics.ListAPIView):
    def __init__(self, **kwargs):
        self.response_format = ResponseInfo().response
        super(GetObservationsApiView, self).__init__(**kwargs)

    serializer_class    = ObservationResponseSchemas
    permission_classes  = [IsAuthenticated]
    pagination_class    = RestPagination

    search = openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                                description="Search by basin, measurement type name, or source")
    basin_id = openapi.Parameter('basin_id', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                                description="Exact basin identifier")
    measurement_type_id = openapi.Parameter('measurement_type_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=False,
                                description="Measurement type ID")
    start_timestamp = openapi.Parameter('start_timestamp', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                                description="Filter observations at or after this timestamp")
    end_timestamp = openapi.Parameter('end_timestamp', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                                description="Filter observations at or before this timestamp")
    value_above = openapi.Parameter('value_above', openapi.IN_QUERY, type=openapi.TYPE_NUMBER, required=False,
                                description="Filter observations with value greater than or equal to this threshold")
    value_below = openapi.Parameter('value_below', openapi.IN_QUERY, type=openapi.TYPE_NUMBER, required=False,
                                description="Filter observations with value less than or equal to this threshold")
    id = openapi.Parameter('id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=False,
                                description="Single observation ID to fetch specific details")

    @swagger_auto_schema(tags=["Observations"], manual_parameters=[search, basin_id, measurement_type_id, start_timestamp, end_timestamp, value_above, value_below, id], pagination_class=RestPagination)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, *args, **kwargs):
        return ObservationService.get_observations(
            search_query=self.request.query_params.get('search'),
            basin_id=self.request.query_params.get('basin_id'),
            measurement_type_id=self.request.query_params.get('measurement_type_id'),
            start_timestamp=self.request.query_params.get('start_timestamp'),
            end_timestamp=self.request.query_params.get('end_timestamp'),
            value_above=self.request.query_params.get('value_above'),
            value_below=self.request.query_params.get('value_below'),
            unique_id=self.request.query_params.get('id'),
        )




class CreateOrUpdateObservationApiView(generics.GenericAPIView):
    def __init__(self, **kwargs):
        self.response_format = ResponseInfo().response
        super(CreateOrUpdateObservationApiView, self).__init__(**kwargs)

    serializer_class    = ObservationCreateUpdateSerializer
    response_schema     = ObservationResponseSchemas
    permission_classes  = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Observations"],
        request_body=ObservationCreateUpdateSerializer,
        responses={200: ObservationResponseSchemas, 201: ObservationResponseSchemas},
        operation_summary="Create or Update Observation",
        operation_description=(
            "Pass `id` in the request body to update an existing observation."
            " Omit `id` (or pass null) to create a new observation."
        )
    )
    def post(self, request, *args, **kwargs):
        try:
            observation_id = request.data.get('id') or None
            serializer = self.serializer_class(data=request.data, context={'id': observation_id})
            if not serializer.is_valid():
                self.response_format['status_code'] = status.HTTP_400_BAD_REQUEST
                self.response_format['status'] = False
                self.response_format['errors'] = serializer.errors
                return Response(self.response_format, status=status.HTTP_400_BAD_REQUEST)

            data = serializer.validated_data.copy()
            data.pop('id', None)

            if observation_id:
                observation = ObservationService.update_observation(
                    observation_id=int(observation_id),
                    validated_data=data,
                    updated_by=request.user,
                )
                http_status = status.HTTP_200_OK
                message = "Observation updated successfully."
            else:
                observation = ObservationService.create_observation(
                    validated_data=data,
                    created_by=request.user,
                )
                http_status = status.HTTP_201_CREATED
                message = "Observation created successfully."

            self.response_format['status_code'] = http_status
            self.response_format['status'] = True
            self.response_format['message'] = message
            self.response_format['data'] = self.response_schema(observation, context={'request': request}).data
            return Response(self.response_format, status=http_status)

        except ValueError as e:
            self.response_format['status_code'] = status.HTTP_400_BAD_REQUEST
            self.response_format['status'] = False
            self.response_format['message'] = str(e)
            return Response(self.response_format, status=status.HTTP_400_BAD_REQUEST)
        except Observation.DoesNotExist:
            self.response_format['status_code'] = status.HTTP_404_NOT_FOUND
            self.response_format['status'] = False
            self.response_format['message'] = "Observation not found."
            return Response(self.response_format, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return ExceptionHandler.handle(e)


class DeleteObservationsApiView(generics.DestroyAPIView):
    def __init__(self, **kwargs):
        self.response_format = ResponseInfo().response
        super(DeleteObservationsApiView, self).__init__(**kwargs)

    serializer_class = ObservationDeleteSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Observations"],
        request_body=ObservationDeleteSerializer,
        operation_description="Pass observation IDs as a comma-separated string, for example: 1,2,3"
    )
    def delete(self, request, *args, **kwargs):
        try:
            serializer = self.serializer_class(data=request.data)
            if not serializer.is_valid():
                self.response_format['status_code'] = status.HTTP_400_BAD_REQUEST
                self.response_format['status'] = False
                self.response_format['errors'] = serializer.errors
                return Response(self.response_format, status=status.HTTP_400_BAD_REQUEST)

            observation_ids = serializer.validated_data['ids']
            ObservationService.delete_observations(observation_ids=observation_ids)

            self.response_format['status_code'] = status.HTTP_200_OK
            self.response_format['status'] = True
            self.response_format['message'] = "Observations deleted successfully."
            return Response(self.response_format, status=status.HTTP_200_OK)

        except Exception as e:
            return ExceptionHandler.handle(e)


class IngestObservationsApiView(generics.GenericAPIView):
    def __init__(self, **kwargs):
        self.response_format = ResponseInfo().response
        super().__init__(**kwargs)

    serializer_class   = IngestObservationsSerializer
    permission_classes = [IsAuthenticated]

    rainfall_file_param = openapi.Parameter(
        'rainfall_file', openapi.IN_FORM, type=openapi.TYPE_FILE, required=False,
        description='january_data_rain.csv — columns: datetime, value, basin',
    )
    temperature_file_param = openapi.Parameter(
        'temperature_file', openapi.IN_FORM, type=openapi.TYPE_FILE, required=False,
        description='january_data_temp.csv — columns: Datetime, Value, Basin.ID',
    )
    auto_create_param = openapi.Parameter(
        'auto_create_basins', openapi.IN_FORM, type=openapi.TYPE_BOOLEAN, required=False,
        description='Auto-create Basin rows for unknown CSV station IDs (default: true)',
    )

    @swagger_auto_schema(
        tags=['Ingestion'],
        manual_parameters=[rainfall_file_param, temperature_file_param, auto_create_param],
        operation_summary='Ingest rainfall and/or temperature CSV observations',
        operation_description=(
            'Upload one or both exam CSV files. '
            'On success returns a simple success message. '
            'On any row/file error the API stops and returns the error.'
        ),
        consumes=['multipart/form-data'],
    )
    def post(self, request, *args, **kwargs):
        try:
            serializer = self.serializer_class(data=request.data)
            if not serializer.is_valid():
                self.response_format['status_code'] = status.HTTP_400_BAD_REQUEST
                self.response_format['status'] = False
                self.response_format['message'] = 'Invalid upload request.'
                self.response_format['data'] = {}
                self.response_format['errors'] = serializer.errors
                return Response(self.response_format, status=status.HTTP_400_BAD_REQUEST)

            auto_create = serializer.validated_data.get('auto_create_basins', True)
            user = request.user if getattr(request.user, 'is_authenticated', False) else None

            rainfall_file = serializer.validated_data.get('rainfall_file')
            if rainfall_file:
                IngestionService.ingest_rainfall(
                    rainfall_file,
                    auto_create_basins=auto_create,
                    created_by=user,
                )

            temperature_file = serializer.validated_data.get('temperature_file')
            if temperature_file:
                IngestionService.ingest_temperature(
                    temperature_file,
                    auto_create_basins=auto_create,
                    created_by=user,
                )

            self.response_format['status_code'] = status.HTTP_200_OK
            self.response_format['status'] = True
            self.response_format['message'] = 'Successfully created.'
            self.response_format['data'] = {}
            self.response_format['errors'] = {}
            return Response(self.response_format, status=status.HTTP_200_OK)

        except IngestionError as e:
            self.response_format['status_code'] = status.HTTP_400_BAD_REQUEST
            self.response_format['status'] = False
            self.response_format['message'] = str(e)
            self.response_format['data'] = {}
            self.response_format['errors'] = [e.as_dict()]
            return Response(self.response_format, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return ExceptionHandler.handle(e)
