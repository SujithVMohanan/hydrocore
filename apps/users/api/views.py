from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from apps.users.models import Users
from apps.users.services.user_service import UserService
from utils.api_utils import (
    ResponseInfo,
    RestPagination

)
from utils.jwt_blacklist import logout_tokens

from apps.users.api.schemas import (
    CreateOrUpdateUserResponseSchema,
    GetUsersApiSchema,
    RegisterUserResponseSchema
)

from apps.users.api.serializers import (
    CreateOrUpdateUserSerializer,
    LoginUserSerializer,
    LogoutUserSerializer,
    RegisterUserSerializer,
    UserDeleteSerializer,
)

from utils.custom_exception import ExceptionHandler


class GetUsersApiView(generics.ListAPIView):

    serializer_class    = GetUsersApiSchema 
    permission_classes  = [IsAuthenticated]
    pagination_class    = RestPagination
    search              = openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                                description="Enter full name or email")
    user_id             = openapi.Parameter('user_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=False,
                                description="single user id to fetch specific user details"
                                )
    
    @swagger_auto_schema(tags=["Users"], manual_parameters=[search, user_id], pagination_class=RestPagination)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, *args, **kwargs):
        search_query = self.request.query_params.get('search')
        user_id      = self.request.query_params.get('user_id')
        return UserService.get_users(search_query=search_query, user_id=user_id)




class RegsiterUserApiView(generics.CreateAPIView):
    def __init__(self, **kwargs):
        self.response_format = ResponseInfo().response
        super(RegsiterUserApiView, self).__init__(**kwargs)

    serializer_class    = RegisterUserSerializer
    response_schema     = RegisterUserResponseSchema

    @swagger_auto_schema(tags=["Users"])
    def post(self, request, *args, **kwargs):
        try:

            serializer = self.serializer_class(data=request.data, context = {'request' : request}) 
            if not serializer.is_valid():
                self.response_format['status_code'] = status.HTTP_400_BAD_REQUEST
                self.response_format["status"] = False
                self.response_format["errors"] = serializer.errors
                return Response(self.response_format, status=status.HTTP_400_BAD_REQUEST)
            
            
            user = UserService.register_user(
                        validated_data=serializer.validated_data
                    )

            refresh         = RefreshToken.for_user(user)
            access_token    = str(refresh.access_token)
            refresh_token   = str(refresh)

                    
            user_data = self.response_schema(user).data

            user_data.update({
                "token"           : access_token,   
                "refresh_token"   : refresh_token,
            })

            self.response_format['status_code']   = status.HTTP_201_CREATED
            self.response_format["message"]       = "User registered successfully."
            self.response_format["status"]        = True
            self.response_format["data"]          = user_data
            return Response(self.response_format, status=status.HTTP_201_CREATED)
            
        
        except Exception as e:
            return ExceptionHandler.handle(e)






class LoginApiView(generics.CreateAPIView):
    def __init__(self, **kwargs):
        self.response_format = ResponseInfo().response
        super(LoginApiView, self).__init__(**kwargs)

    serializer_class = LoginUserSerializer
    response_schema  = RegisterUserResponseSchema

    @swagger_auto_schema(tags=["Authentication"])
    def post(self, request, *args, **kwargs):
        try:
            serializer = self.serializer_class(data=request.data, context={'request': request})
            if not serializer.is_valid():
                self.response_format['status_code'] = status.HTTP_400_BAD_REQUEST
                self.response_format["status"] = False
                self.response_format["errors"] = serializer.errors
                return Response(self.response_format, status=status.HTTP_400_BAD_REQUEST)

            user            = serializer.validated_data['user']
            refresh         = RefreshToken.for_user(user)
            access_token    = str(refresh.access_token)
            refresh_token   = str(refresh)

            user_data = self.response_schema(user).data
            user_data.update({
                "token"           : access_token,
                "refresh_token"   : refresh_token,
            })


            self.response_format['status_code']   = status.HTTP_200_OK
            self.response_format["message"]       = "Login successful."
            self.response_format["status"]        = True
            self.response_format["data"]          = user_data
            return Response(self.response_format, status=status.HTTP_200_OK)

        except Exception as e:
            return ExceptionHandler.handle(e)



        except Exception as e:
            return ExceptionHandler.handle(e)



class LogoutApiView(generics.GenericAPIView):
    def __init__(self, **kwargs):
        self.response_format = ResponseInfo().response
        super().__init__(**kwargs)

    serializer_class    = LogoutUserSerializer
    permission_classes  = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Authentication"],
        request_body=LogoutUserSerializer,
        operation_summary="Logout and expire tokens",
        operation_description=(
            "Requires `Authorization: Bearer <access_token>`.\n\n"
            "Pass the `refresh_token` from login/register in the body. "
            "Both the access token and refresh token are expired/blacklisted so they cannot be reused."
        ),
    )
    def post(self, request, *args, **kwargs):
        try:
            serializer = self.serializer_class(data=request.data)
            if not serializer.is_valid():
                self.response_format['status_code'] = status.HTTP_400_BAD_REQUEST
                self.response_format['status'] = False
                self.response_format['errors'] = serializer.errors
                return Response(self.response_format, status=status.HTTP_400_BAD_REQUEST)

            auth_header  = request.META.get('HTTP_AUTHORIZATION', '')
            access_token = None
            if auth_header.lower().startswith('bearer '):
                access_token = auth_header.split(' ', 1)[1].strip()

            try:
                logout_tokens(
                    access_token=access_token,
                    refresh_token=serializer.validated_data['refresh_token'],
                )
            except TokenError as exc:
                self.response_format['status_code'] = status.HTTP_400_BAD_REQUEST
                self.response_format['status'] = False
                self.response_format['message'] = str(exc)
                self.response_format['errors'] = {'refresh_token': [str(exc)]}
                return Response(self.response_format, status=status.HTTP_400_BAD_REQUEST)

            self.response_format['status_code'] = status.HTTP_200_OK
            self.response_format['status'] = True
            self.response_format['message'] = "Logout successful. Tokens have been expired."
            self.response_format['data'] = {}
            self.response_format['errors'] = []
            return Response(self.response_format, status=status.HTTP_200_OK)

        except Exception as e:
            return ExceptionHandler.handle(e)


class DeleteUsersApiView(generics.DestroyAPIView):
    def __init__(self, **kwargs):
        self.response_format = ResponseInfo().response
        super(DeleteUsersApiView, self).__init__(**kwargs)

    serializer_class   = UserDeleteSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Users"],
        request_body=UserDeleteSerializer,
        operation_description="Pass user IDs as a comma-separated string, for example: 1,2,3"
    )
    def delete(self, request, *args, **kwargs):
        try:
            serializer = self.serializer_class(data=request.data)
            if not serializer.is_valid():
                self.response_format['status_code'] = status.HTTP_400_BAD_REQUEST
                self.response_format["status"] = False
                self.response_format["errors"] = serializer.errors
                return Response(self.response_format, status=status.HTTP_400_BAD_REQUEST)

            user_ids = serializer.validated_data['user_ids']
            UserService.delete_users(user_ids=user_ids)

            self.response_format['status_code']   = status.HTTP_200_OK
            self.response_format["message"]       = "Users deleted successfully."
            self.response_format["status"]        = True
            return Response(self.response_format, status=status.HTTP_200_OK)

        except Exception as e:
            return ExceptionHandler.handle(e)


class CreateOrUpdateUserApiView(generics.GenericAPIView):
    def __init__(self, **kwargs):
        self.response_format = ResponseInfo().response
        super(CreateOrUpdateUserApiView, self).__init__(**kwargs)

    serializer_class   = CreateOrUpdateUserSerializer
    response_schema    = CreateOrUpdateUserResponseSchema
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Users"],
        request_body=CreateOrUpdateUserSerializer,
        responses={200: CreateOrUpdateUserResponseSchema, 201: CreateOrUpdateUserResponseSchema},
        operation_summary="Create or Update User",
        operation_description=(
            "Pass `user_id` in the request body to **update** an existing user.\n\n"
            "Omit `user_id` (or pass null) to **create** a new user."
        )
    )
    
    def post(self, request, *args, **kwargs):
        try:
            user_id = request.data.get('user_id') or None

            serializer = self.serializer_class(
                data=request.data,
                context={'request': request, 'user_id': user_id}
            )

            if not serializer.is_valid():
                self.response_format['status_code'] = status.HTTP_400_BAD_REQUEST
                self.response_format['status']      = False
                self.response_format['errors']      = serializer.errors
                return Response(self.response_format, status=status.HTTP_400_BAD_REQUEST)

            # Strip user_id from data before passing to service
            data = serializer.validated_data.copy()
            data.pop('user_id', None)

            if user_id:
                
                try:
                    user = UserService.update_user(
                        user_id=int(user_id),
                        validated_data=data,
                        updated_by=request.user
                    )
                except Users.DoesNotExist:
                    self.response_format['status_code'] = status.HTTP_404_NOT_FOUND
                    self.response_format['status']      = False
                    self.response_format['message']     = "User not found."
                    return Response(self.response_format, status=status.HTTP_404_NOT_FOUND)

                http_status = status.HTTP_200_OK
                message     = "User updated successfully."

            else:
                user = UserService.create_user(
                    validated_data=data,
                    created_by=request.user
                )
                http_status = status.HTTP_201_CREATED
                message     = "User created successfully."

            self.response_format['status_code'] = http_status
            self.response_format['status']      = True
            self.response_format['message']     = message
            self.response_format['data']        = self.response_schema(user, context={'request': request}).data
            return Response(self.response_format, status=http_status)

        except Exception as e:
            return ExceptionHandler.handle(e)