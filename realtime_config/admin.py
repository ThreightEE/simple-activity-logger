# type: ignore

from django.contrib import admin
from .models import ConfigChangeLog

from typing import Optional, Tuple
from django.http import HttpRequest


@admin.register(ConfigChangeLog)
class ConfigChangeLogAdmin(admin.ModelAdmin):
    list_display: Tuple[str, ...] = ('key', 'old_value', 'new_value', 'changed_at')
    list_filter: Tuple[str, ...] = ('key', 'changed_at')
    search_fields: Tuple[str, ...] = ('key', 'new_value')
    readonly_fields: Tuple[str, ...] = ('key', 'old_value', 'new_value', 'changed_at')
    
    def has_add_permission(
            self, request: HttpRequest
        ) -> bool:
        return False

    def has_change_permission(
            self, request: HttpRequest, obj: Optional[ConfigChangeLog] = None
        ) -> bool:
        return False
