from django.urls import path
from . import views

from typing import List
from django.urls.resolvers import URLPattern


app_name: str = 'config_app'

urlpatterns: List[URLPattern] = [
    path('', views.home, name='home'),
    path('api/configs/', views.get_all_configs_api, name='get_all_configs_api'),
    path('api/logs/', views.get_change_logs_api, name='get_change_logs_api'),
]
