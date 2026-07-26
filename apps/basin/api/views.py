import os, sys
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.response import Response
from apps.basin.models import Basin
from apps.basin.services.basin_service import BasinService
from utils.api_utils import (
    ResponseInfo,
    RestPagination
)

from apps.basin.api.serializers import (
    BasinCreateUpdateSerializer,
    BasinDeleteSerializer,
)
from apps.basin.api.sechams import (
    BasinResponseSchemas,
)

from utils.custom_exception import ExceptionHandler



class GetBasinsApiView(generics.ListAPIView):

    serializer_class    = BasinResponseSchemas
    permission_classes  = [IsAuthenticated]
    pagination_class    = RestPagination
    search              = openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                                description="Enter basin ID or name")
    basin_id            = openapi.Parameter('basin_id', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                                description="Single basin identifier to fetch specific basin details"
                                )
    id                  = openapi.Parameter('id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=False,
                                description="Single basin ID to fetch specific basin details"
                                )

    @swagger_auto_schema(tags=["Basin"], manual_parameters=[search, basin_id], pagination_class=RestPagination)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, *args, **kwargs):

        search_query = self.request.query_params.get('search')
        basin_id     = self.request.query_params.get('basin_id')
        unique_id    = self.request.query_params.get('id')

        return BasinService.get_basins(
                    search_query=search_query, 
                    basin_id=basin_id,
                    unique_id=unique_id
                    )




class CreateOrUpdateBasinApiView(generics.GenericAPIView):
    def __init__(self, **kwargs):
        self.response_format = ResponseInfo().response
        super(CreateOrUpdateBasinApiView, self).__init__(**kwargs)

    serializer_class   = BasinCreateUpdateSerializer
    response_schema    = BasinResponseSchemas
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Basin"],
        request_body=BasinCreateUpdateSerializer,
        responses={200: BasinResponseSchemas, 201: BasinResponseSchemas},
        operation_summary="Create or Update Basin",
        operation_description=(
            "Pass `id` in the request body to **update** an existing basin.\n\n"
            "Omit `id` (or pass null) to **create** a new basin."
        )
    )
    def post(self, request, *args, **kwargs):
        try:
            basin_id = request.data.get('id') or None

            serializer = self.serializer_class(
                data=request.data,
                context={'request': request, 'id': basin_id}
            )

            if not serializer.is_valid():
                self.response_format['status_code'] = status.HTTP_400_BAD_REQUEST
                self.response_format['status']      = False
                self.response_format['errors']      = serializer.errors
                return Response(self.response_format, status=status.HTTP_400_BAD_REQUEST)

            data = serializer.validated_data.copy()
            data.pop('id', None)

            if basin_id:
                try:
                    basin = BasinService.update_basin(
                        basin_id=int(basin_id),
                        validated_data=data,
                        updated_by=request.user
                    )
                except Basin.DoesNotExist:
                    self.response_format['status_code'] = status.HTTP_404_NOT_FOUND
                    self.response_format['status']      = False
                    self.response_format['message']     = "Basin not found."
                    return Response(self.response_format, status=status.HTTP_404_NOT_FOUND)

                http_status = status.HTTP_200_OK
                message     = "Basin updated successfully."

            else:
                basin = BasinService.create_basin(
                    validated_data=data,
                    created_by=request.user
                )
                http_status = status.HTTP_201_CREATED
                message     = "Basin created successfully."

            self.response_format['status_code'] = http_status
            self.response_format['status']      = True
            self.response_format['message']     = message
            self.response_format['data']        = self.response_schema(basin, context={'request': request}).data
            return Response(self.response_format, status=http_status)

        except Exception as e:
            return ExceptionHandler.handle(e)



class DeleteBasinsApiView(generics.DestroyAPIView):
    def __init__(self, **kwargs):
        self.response_format = ResponseInfo().response
        super(DeleteBasinsApiView, self).__init__(**kwargs)

    serializer_class   = BasinDeleteSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Basin"],
        request_body=BasinDeleteSerializer,
        operation_description="Pass basin IDs as a comma-separated string, for example: 1,2,3"
    )
    def delete(self, request, *args, **kwargs):
        try:
            serializer = self.serializer_class(data=request.data)
            if not serializer.is_valid():
                self.response_format['status_code'] = status.HTTP_400_BAD_REQUEST
                self.response_format['status'] = False
                self.response_format['errors'] = serializer.errors
                return Response(self.response_format, status=status.HTTP_400_BAD_REQUEST)

            basin_ids = serializer.validated_data['ids']
            BasinService.delete_basins(basin_ids=basin_ids)

            self.response_format['status_code']   = status.HTTP_200_OK
            self.response_format['message']       = "Basins deleted successfully."
            self.response_format['status']        = True
            return Response(self.response_format, status=status.HTTP_200_OK)

        except Exception as e:
            return ExceptionHandler.handle(e)
