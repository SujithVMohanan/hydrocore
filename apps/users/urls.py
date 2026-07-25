from django.urls import path


from apps.users.api.views import (
    DeleteUsersApiView,
    GetUsersApiView,
    RegsiterUserApiView,
    LoginApiView,
    CreateOrUpdateUserApiView,
)

urlpatterns = [




    # API Endpoints for User Management
    path('get-users/', GetUsersApiView.as_view(), name='user-list'),
    path('register-user/', RegsiterUserApiView.as_view(), name='user-register'),
    path('login/', LoginApiView.as_view(), name='user-login'),
    path('delete/', DeleteUsersApiView.as_view(), name='user-delete'),
    path('create-or-update-user/', CreateOrUpdateUserApiView.as_view(), name='user-create-or-update'),

]
