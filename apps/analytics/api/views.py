from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.response import Response

from apps.analytics.api.sechams import TimeseriesPointSchemas
from apps.analytics.services.rainfall_event_service import RainfallEventService
from apps.analytics.api.serializers import (
    RainfallEventResponseSchema,
    RainfallEventDeleteSerializer,
    DetectEventsResponseSerializer,
)
from utils.api_utils import (
    ResponseInfo, 
    RestPagination
)

from apps.users.models import Users
from utils.custom_exception import ExceptionHandler


class GetRainfallEventsApiView(generics.ListAPIView):
    serializer_class = RainfallEventResponseSchema
    permission_classes = [IsAuthenticated]
    pagination_class = RestPagination

    search = openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                                description="Search by basin ID, peak value, or total volume")
    basin_id = openapi.Parameter('basin_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=False,
                                description="Filter by basin primary key ID")
    start_timestamp = openapi.Parameter('start_timestamp', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                                description="Filter events starting at or after this timestamp")
    end_timestamp = openapi.Parameter('end_timestamp', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                                description="Filter events ending at or before this timestamp")
    min_dry_gap_used = openapi.Parameter('min_dry_gap_used', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=False,
                                description="Filter by minimum dry gap used")
    id = openapi.Parameter('id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=False,
                                description="Single rainfall event ID to fetch specific details")

    @swagger_auto_schema(tags=["RainfallEvents"], manual_parameters=[search, basin_id, start_timestamp, end_timestamp, min_dry_gap_used, id], pagination_class=RestPagination)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, *args, **kwargs):
        return RainfallEventService.get_rainfall_events(
            search_query        = self.request.query_params.get('search'),
            basin_id            = self.request.query_params.get('basin_id'),
            start_timestamp     = self.request.query_params.get('start_timestamp'),
            end_timestamp       = self.request.query_params.get('end_timestamp'),
            min_dry_gap_used    = self.request.query_params.get('min_dry_gap_used'),
            unique_id           = self.request.query_params.get('id'),
        )


class DeleteRainfallEventsApiView(generics.DestroyAPIView):
    def __init__(self, **kwargs):
        self.response_format = ResponseInfo().response
        super(DeleteRainfallEventsApiView, self).__init__(**kwargs)

    serializer_class   = RainfallEventDeleteSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["RainfallEvents"],
        request_body=RainfallEventDeleteSerializer,
        operation_description="Pass rainfall event IDs as a comma-separated string, for example: 1,2,3"
    )
    def delete(self, request, *args, **kwargs):
        try:
            serializer = self.serializer_class(data=request.data)
            if not serializer.is_valid():
                self.response_format['status_code'] = status.HTTP_400_BAD_REQUEST
                self.response_format['status'] = False
                self.response_format['errors'] = serializer.errors
                return Response(self.response_format, status=status.HTTP_400_BAD_REQUEST)

            event_ids = serializer.validated_data['ids']
            RainfallEventService.delete_rainfall_events(event_ids=event_ids)

            self.response_format['status_code'] = status.HTTP_200_OK
            self.response_format['status'] = True
            self.response_format['message'] = "Rainfall events deleted successfully."
            return Response(self.response_format, status=status.HTTP_200_OK)

        except ValueError as e:
            self.response_format['status_code'] = status.HTTP_400_BAD_REQUEST
            self.response_format['status'] = False
            self.response_format['message'] = str(e)
            return Response(self.response_format, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return ExceptionHandler.handle(e)


class GetTimeseriesApiView(generics.ListAPIView):

    serializer_class    = TimeseriesPointSchemas
    permission_classes  = [IsAuthenticated]
    pagination_class    = RestPagination

    measurement_id = openapi.Parameter('measurement_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True,
                                description="Measurement type id (integer)")
    start = openapi.Parameter('start', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                                description="Start timestamp (inclusive)")
    end = openapi.Parameter('end', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                                description="End timestamp (inclusive)")

    @swagger_auto_schema(tags=["RainfallEvents"], manual_parameters=[measurement_id, start, end], pagination_class=RestPagination)
    def get(self, request, basin_id, *args, **kwargs):
        try:
            measurement_id = request.query_params.get('measurement_id')
            if not measurement_id:
                return Response(ResponseInfo().bad_request("measurement_id is required"), status=status.HTTP_400_BAD_REQUEST)

            return super().get(request, *args, **kwargs)
        except Exception as e:
            return ExceptionHandler.handle(e)

    def get_queryset(self, *args, **kwargs):

        measurement_id    = self.request.query_params.get('measurement_id')
        start             = self.request.query_params.get('start')
        end               = self.request.query_params.get('end')

        return RainfallEventService.get_timeseries(
            basin_id=int(self.kwargs.get('basin_id')),
            measurement_type_id=int(measurement_id),
            start_timestamp=start,
            end_timestamp=end,
        )



class DetectRainfallEventsApiView(generics.GenericAPIView):
    
    permission_classes    = [IsAuthenticated]
    serializer_class      = DetectEventsResponseSerializer

    def __init__(self, **kwargs):
        self.response_format = ResponseInfo().response
        super(DetectRainfallEventsApiView, self).__init__(**kwargs)

    min_dry_gap = openapi.Parameter('min_dry_gap_hours', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True,
                                description="Minimum dry gap hours to split events")

    @swagger_auto_schema(tags=["RainfallEvents"], manual_parameters=[min_dry_gap], request_body=openapi.Schema(type=openapi.TYPE_OBJECT), responses={200: DetectEventsResponseSerializer()})
    def post(self, request, basin_id, *args, **kwargs):
        try:
            
            min_dry_gap       = request.query_params.get('min_dry_gap_hours')
            measurement_id    = request.data.get('measurement_id') or request.query_params.get('measurement_id')
            start             = request.data.get('start') or request.query_params.get('start')
            end               = request.data.get('end') or request.query_params.get('end')

            if not min_dry_gap:
                return Response(ResponseInfo().bad_request("min_dry_gap_hours is required"), status=status.HTTP_400_BAD_REQUEST)
            if not measurement_id:
                return Response(ResponseInfo().bad_request("measurement_id is required"), status=status.HTTP_400_BAD_REQUEST)

            user = request.user
            if not getattr(user, "is_authenticated", False) or not isinstance(user, Users):
                user = None

            result = RainfallEventService.detect_and_persist_events(
                basin_id=int(basin_id),
                min_dry_gap_hours=int(min_dry_gap),
                measurement_type_id=int(measurement_id),
                created_by=user,
                start_timestamp=start,
                end_timestamp=end,
            )

            serializer = DetectEventsResponseSerializer(result)

            self.response_format['status_code'] = status.HTTP_200_OK
            self.response_format['status'] = True
            self.response_format['message'] = ""
            self.response_format['data'] = serializer.data
            self.response_format['errors'] = {}
            return Response(self.response_format, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(ResponseInfo().bad_request(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return ExceptionHandler.handle(e)
