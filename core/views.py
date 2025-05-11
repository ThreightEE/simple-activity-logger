from django.shortcuts import render

import logging
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView
from django.urls import reverse_lazy
from .models import Activity
from .forms import ActivityForm
from .enums import ProcessingStatus

from django.db import transaction
from .tasks import process_activity

from django.http import JsonResponse
from .monitoring import get_counter

from realtime_config.realtime_config import get_config


logger = logging.getLogger(__name__)


class ActivityListView(ListView):
    """
    Show list of activities divided into pages.
    """
    model = Activity
    template_name = 'core/activity_list.html'
    context_object_name = 'activities'
    
    def get_paginate_by(self, queryset):
        """
        Realtime config for activities display per page.
        """
        return int(get_config('ACTIVITIES_PER_PAGE', 9))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pending_count'] = Activity.objects.filter(
            status=ProcessingStatus.PENDING
        ).count()

        # Realtime config
        context['polling_interval'] = float(get_config('ACTIVITY_POLLING_S', 2.0)) \
            * 1000
        return context


class ActivityDetailView(DetailView):
    """
    Show information about single activity.
    """
    model = Activity
    template_name = 'core/activity_detail.html'
    context_object_name = 'activity'


class ActivityCreateView(CreateView):
    """
    Creation of activity.
    """
    model = Activity
    form_class = ActivityForm
    template_name = 'core/activity_form.html'
    success_url = reverse_lazy('activity-list')
    
    def form_valid(self, form):
        """
        Saves form after submission if it's valid. Calls celery task.
        """

        # Ensure both or neither saving model and queuing task
        with transaction.atomic():
            # Save form normally
            response = super().form_valid(form)
            # Get the new activity instance
            activity = self.object

            try:
                # Queue task with default options and get its id
                task_result = process_activity.delay(activity.id)

                # Store id in the model
                activity.celery_task_id = task_result.id
                activity.save(update_fields=['celery_task_id'])

                # Log the creation
                logger.info(
                    f"New activity created: {activity.id} ({activity.activity_type}), "
                    f"and queued for processing with task {task_result.id}"
                )
            except Exception as e:
                logger.info(f"Processing activity {activity.id} synchronously "
                            "due to Redis unavailability")
                try:
                    activity.update_status(ProcessingStatus.PROCESSING)
                    calories = activity.calculate_calories()
                    if calories is not None:
                        activity.update_status(ProcessingStatus.COMPLETED, calories=calories)
                        messages.success(self.request, "Activity processed locally (Redis unavailable)")
                    else:
                        activity.update_status(
                            ProcessingStatus.FAILED, 
                            error_msg="Failed to calculate calories"
                        )
                        messages.warning(self.request, "Could not calculate calories")
                except Exception as process_error:
                    logger.error(f"Error processing activity synchronously: {process_error}")
                    activity.update_status(
                        ProcessingStatus.FAILED, 
                        error_msg=f"Local processing error: {str(process_error)}"
                    )
                    messages.error(self.request, "Failed to process activity")           

        messages.success(
            self.request, 
            "Activity logged successfully and queued for processing."
        )
        
        return response


# Real-time update

def activity_status_api(request, pk):
    activity = get_object_or_404(Activity, pk=pk)
    return JsonResponse({
        'status': activity.status,
        'status_display': activity.get_status_display(),
        'calories': float(activity.calories_burned) if activity.calories_burned else None,
        'processed_at': activity.processed_at.isoformat() if activity.processed_at else None,
        'error': activity.error_message or None,
        'updated_at': activity.updated_at.isoformat(),
    })

def activity_list_api(request):
    raw_ids = request.GET.get('ids', '')
    valid_ids = []
    
    for id_str in raw_ids.split(','):
        try:
            if id_str.strip():
                valid_ids.append(int(id_str))
        except (ValueError, TypeError):
            continue
    
    activities = Activity.objects.filter(pk__in=valid_ids) if valid_ids else []
    data = {
        str(activity.id): {
            'status': activity.status,
            'status_display': activity.get_status_display(),
            'calories': float(activity.calories_burned) if activity.calories_burned else None
        }
        for activity in activities
    }
    return JsonResponse(data)


def metrics_json(request):
    data = {
        'tasks_started': get_counter('tasks_started'),
        'tasks_completed': get_counter('tasks_completed'),
        'tasks_failed': get_counter('tasks_failed'),
        'total_calories': get_counter('total_calories'),
    }
    return JsonResponse(data)
