from django.urls import path

from apps.users.views import DashboardView

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='user-dashboard'),
]
