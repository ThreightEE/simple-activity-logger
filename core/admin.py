from django.contrib import admin

from .models import Activity

# Register your models here.

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'activity_type',
        'duration_minutes',
        'status',
        'created_at',
        'calories_burned')
    
    list_filter = ('status', 'activity_type')
    search_fields = ('notes',)
    readonly_fields = (
        'created_at', 
        'updated_at', 
        'processed_at', 
        'celery_task_id', 
        'calories_burned',
        'status',
        'error_message'
    )
