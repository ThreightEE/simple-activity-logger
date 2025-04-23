from django.urls import path
from . import views

urlpatterns = [
    path('', views.ActivityListView.as_view(), name='activity-list'),
    path('activity/<int:pk>/', views.ActivityDetailView.as_view(), name='activity-detail'),
    path('activity/create/', views.ActivityCreateView.as_view(), name='activity-create'),
    # API endpoints
    path('api/activity/<int:pk>/status/', views.activity_status_api, name='activity-status-api'),
    path('api/activities/status/', views.activity_list_api, name='activity-list-api'),
]
