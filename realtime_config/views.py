from django.shortcuts import render
from django.conf import settings

from . import realtime_config
from django.http import HttpRequest, HttpResponse, JsonResponse
from typing import Any, Dict, List, Union

from .models import ConfigChangeLog


def home(request: HttpRequest) -> HttpResponse:
    """
    Demo page to view current constance configs.
    """

    config_keys: list[str] = list(settings.CONSTANCE_CONFIG.keys())

    configs: Dict[str, Any] = {key: realtime_config.get_config(key) \
                               for key in config_keys}

    context: Dict[str, Any] = {
        'site_name': configs.get('SITE_NAME') or "",
        'theme_color': configs.get('THEME_COLOR') or "#ffffff",
        'welcome_message': configs.get('WELCOME_MESSAGE') or "",
        'maintenance_mode': configs.get('MAINTENANCE_MODE') or False,
        'items_per_page': configs.get('ITEMS_PER_PAGE') or 10,
        'show_logs': configs.get('SHOW_LOGS') or False,
        'polling_s': configs.get('UI_POLLING_INTERVAL') or 300.0,
        'configs': configs,
    }

    return render(request, 'realtime_config/home.html', context)


def get_all_configs_api(request: HttpRequest) -> JsonResponse:
    """
    API endpoint that returns current config values as JSON.
    """
    keys: list[str] = list(settings.CONSTANCE_CONFIG.keys())
    configs: Dict[str, Any] = {key: realtime_config.get_config(key) for key in keys}
    return JsonResponse(configs)


def get_change_logs_api(request: HttpRequest) -> JsonResponse:
    """
    API endpoint that returns recent LOGS_COUNT config change logs.
    """
    max_logs_str = realtime_config.get_config('LOGS_COUNT', default='10')
    max_logs = int(max_logs_str)
    if max_logs <= 0:
        max_logs = 10

    logs: Any = ConfigChangeLog.objects.all()[:max_logs]

    data: List[Dict[str, Union[int, str, None]]] = [{
        'id': log.id,
        'key': log.key,
        'old_value': log.old_value,
        'new_value': log.new_value,
        'changed_at': log.changed_at.strftime('%Y-%m-%d %H:%M:%S')
    } for log in logs]

    return JsonResponse({'logs': data})
