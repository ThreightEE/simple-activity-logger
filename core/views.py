from django.shortcuts import render

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView
from django.urls import reverse_lazy
from .models import Activity
from .forms import ActivityForm
# from .tasks import process activity method for celery
from .enums import ProcessingStatus

# Create your views here.

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
    Creation of activities.
    """
    model = Activity
    form_class = ActivityForm
    template_name = 'core/activity_form.html'
    success_url = reverse_lazy('activity-list')
    
    def form_valid(self, form):
        """
        Save the form.

        TO DO: add Celery task call ! ! ! ! !
        """
        response = super().form_valid(form)
        # Get the new activity instance
        activity = self.object
        # Log the creation
        logger.info(f"New activity created: {activity.id} ({activity.activity_type})")
        
        # Add success message
        messages.success(
            self.request, 
            "Activity logged successfully [and is queued for processing]."
        )
        
        return response
