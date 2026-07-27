from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.response import Response

from apps.analytics.services.rainfall_event_service import RainfallEventService
from apps.analytics.api.schemas import (
    EventComparisonSchema,
    EventSummarySchema,
    RainfallEventSchema,
    TimeseriesPointSchema,
)
from apps.analytics.api.serializers import (
    DetectEventsResponseSerializer,
    RainfallEventDeleteSerializer,
)
from utils.api_utils import (
    ResponseInfo, 
    RestPagination
)

from apps.users.models import Users
from utils.custom_exception import ExceptionHandler


class GetRainfallEventsApiView(generics.ListAPIView):
    
    serializer_class    = RainfallEventSchema
    permission_classes  = [IsAuthenticated]
    pagination_class    = RestPagination

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
    min_total_volume = openapi.Parameter('min_total_volume', openapi.IN_QUERY, type=openapi.TYPE_NUMBER, required=False,
                                description="Minimum total event volume filter")
    id = openapi.Parameter('id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=False,
                                description="Single rainfall event ID to fetch specific details")

    @swagger_auto_schema(tags=["RainfallEvents"], manual_parameters=[search, basin_id, start_timestamp, end_timestamp, min_dry_gap_used, min_total_volume, id], pagination_class=RestPagination)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, *args, **kwargs):
        basin_id = self.kwargs.get('basin_id') or self.request.query_params.get('basin_id')
        return RainfallEventService.get_rainfall_events(
            search_query        = self.request.query_params.get('search'),
            basin_id            = basin_id,
            start_timestamp     = self.request.query_params.get('start_timestamp'),
            end_timestamp       = self.request.query_params.get('end_timestamp'),
            min_dry_gap_used    = self.request.query_params.get('min_dry_gap_used'),
            min_total_volume    = self.request.query_params.get('min_total_volume'),
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

    serializer_class    = TimeseriesPointSchema
    permission_classes  = [IsAuthenticated]
    pagination_class    = RestPagination

    measurement_id = openapi.Parameter('measurement_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True,
                                description="Measurement type id (integer)")
    measurement_type = openapi.Parameter('measurement_type', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                                description="Measurement type name, for example rainfall or temperature")
    start = openapi.Parameter('start', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                                description="Start timestamp (inclusive)")
    end = openapi.Parameter('end', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                                description="End timestamp (inclusive)")
    from_param = openapi.Parameter('from', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                                description="Start date/time, PDF-style parameter")
    to_param = openapi.Parameter('to', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                                description="End date/time, PDF-style parameter")

    @swagger_auto_schema(tags=["RainfallEvents"], manual_parameters=[measurement_id, measurement_type, start, end, from_param, to_param], pagination_class=RestPagination)
    def get(self, request, basin_id, *args, **kwargs):
        try:
            measurement_id = request.query_params.get('measurement_id')
            measurement_type = request.query_params.get('measurement_type')
            if not measurement_id and not measurement_type:
                return Response(ResponseInfo().bad_request("measurement_id or measurement_type is required"), status=status.HTTP_400_BAD_REQUEST)

            return super().get(request, *args, **kwargs)
        except Exception as e:
            return ExceptionHandler.handle(e)


    def get_queryset(self, *args, **kwargs):
        measurement_id    = self.request.query_params.get('measurement_id')
        measurement_type  = self.request.query_params.get('measurement_type')
        start             = self.request.query_params.get('start') or self.request.query_params.get('from')
        end               = self.request.query_params.get('end') or self.request.query_params.get('to')

        if measurement_type and not measurement_id:
            return RainfallEventService.get_timeseries_by_measurement_name(
                basin_id=int(self.kwargs.get('basin_id')),
                measurement_type=measurement_type,
                from_timestamp=start,
                to_timestamp=end,
            )

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


class BasinEventSummaryApiView(generics.GenericAPIView):

    permission_classes = [IsAuthenticated]
    serializer_class   = EventSummarySchema

    def __init__(self, **kwargs):
        self.response_format = ResponseInfo().response
        super().__init__(**kwargs)

    min_dry_gap = openapi.Parameter(
        'min_dry_gap_hours',
        openapi.IN_QUERY,
        type=openapi.TYPE_INTEGER,
        required=False,
        description='Optional dry-gap filter used when events were detected (hours)',
    )

    @swagger_auto_schema(
        tags=['RainfallEvents'],
        manual_parameters=[min_dry_gap],
        operation_summary='Basin rainfall event summary',
        operation_description=(
            'Return aggregate statistics for detected rainfall events in a basin: '
            'total count, mean duration, mean volume, peak event, and longest event.'
        ),
        responses={200: EventSummarySchema()},
    )
    def get(self, request, basin_id, *args, **kwargs):
        try:
            min_dry_gap       = request.query_params.get('min_dry_gap_hours')
            min_dry_gap_hours = int(min_dry_gap) if min_dry_gap not in (None, '') else None

            result = RainfallEventService.get_event_summary(
                basin_id=int(basin_id),
                min_dry_gap_hours=min_dry_gap_hours,
            )
            serializer = self.serializer_class(result)

            self.response_format['status_code'] = status.HTTP_200_OK
            self.response_format['status'] = True
            self.response_format['message'] = 'Event summary fetched successfully.'
            self.response_format['data'] = serializer.data
            self.response_format['errors'] = {}
            return Response(self.response_format, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response(ResponseInfo().bad_request(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return ExceptionHandler.handle(e)


class EventTimeseriesApiView(generics.ListAPIView):

    serializer_class    = TimeseriesPointSchema
    permission_classes  = [IsAuthenticated]
    pagination_class    = RestPagination

    @swagger_auto_schema(
        tags=['RainfallEvents'],
        operation_summary='Rainfall event detail timeseries',
        operation_description='Return full hourly rainfall timeseries for a specific event window.',
        pagination_class=RestPagination,
    )
    def get_queryset(self, *args, **kwargs):
        return RainfallEventService.get_event_timeseries(
            event_id=int(self.kwargs.get('event_id')),
        )


class EventComparisonApiView(generics.GenericAPIView):

    permission_classes    = [IsAuthenticated]
    serializer_class      = EventComparisonSchema

    def __init__(self, **kwargs):
        self.response_format = ResponseInfo().response
        super().__init__(**kwargs)

    gaps = openapi.Parameter(
        'gaps',
        openapi.IN_QUERY,
        type=openapi.TYPE_STRING,
        required=True,
        description='Comma-separated dry-gap hours, for example 3,6,12',
    )

    @swagger_auto_schema(
        tags=['RainfallEvents'],
        manual_parameters=[gaps],
        operation_summary='Compare event summaries across multiple dry-gap values',
        responses={200: EventComparisonSchema()},
    )
    def get(self, request, basin_id, *args, **kwargs):
        try:
            raw_gaps = request.query_params.get('gaps', '')
            if not raw_gaps.strip():
                return Response(ResponseInfo().bad_request("gaps is required"), status=status.HTTP_400_BAD_REQUEST)
            gaps = [int(g.strip()) for g in raw_gaps.split(',') if g.strip()]
            result = RainfallEventService.get_event_comparison(int(basin_id), gaps)
            serializer = self.serializer_class(result)

            self.response_format['status_code'] = status.HTTP_200_OK
            self.response_format['status'] = True
            self.response_format['message'] = 'Event comparison fetched successfully.'
            self.response_format['data'] = serializer.data
            self.response_format['errors'] = {}
            return Response(self.response_format, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(ResponseInfo().bad_request(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return ExceptionHandler.handle(e)
