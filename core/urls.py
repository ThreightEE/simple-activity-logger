from django.urls import path
from . import views

urlpatterns = [
    path('', views.ActivityListView.as_view(), name='activity-list'),
    path('activity/<int:pk>/', views.ActivityDetailView.as_view(), name='activity-detail'),
    path('activity/create/', views.ActivityCreateView.as_view(), name='activity-create'),
]
