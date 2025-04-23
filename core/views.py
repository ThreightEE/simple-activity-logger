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


listview_paginate = 10

logger = logging.getLogger(__name__)


class ActivityListView(ListView):
    """
    Show list of activities divided into pages.
    """
    model = Activity
    template_name = 'core/activity_list.html'
    context_object_name = 'activities'
    paginate_by = listview_paginate
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add count of pending activities to context
        context['pending_count'] = Activity.objects.filter(
            status=ProcessingStatus.PENDING
        ).count()
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

        messages.success(
            self.request, 
            "Activity logged successfully and queued for processing."
        )
        
        return response
