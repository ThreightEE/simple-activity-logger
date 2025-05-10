from django import forms
from .models import Activity
from .enums import ActivityType

from realtime_config.realtime_config import get_config


class ActivityForm(forms.ModelForm):
    """
    Form for creating Activity Log.
    Built from Activity model.
    """

    class Meta:
        model = Activity
        fields = ['activity_type', 'duration_minutes', 'weight_kg', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove empty choice
        self.fields['activity_type'].choices = ActivityType.choices()
        self.fields['activity_type'].empty_label = None
        
        # Set default weight from realtime config
        if not self.initial.get('weight_kg'):
            self.initial['weight_kg'] = get_config('DEFAULT_WEIGHT', 70.0)


    def clean_activity_type(self):
        activity_type = self.cleaned_data.get('activity_type')
        return ActivityType.validate(activity_type)
    
    def clean_duration_minutes(self):
        duration = self.cleaned_data.get('duration_minutes')
        if duration is not None and duration <= 0:
            raise forms.ValidationError("Duration must be positive")
        return duration
    
    def clean_weight_kg(self):
        weight = self.cleaned_data.get('weight_kg')
        if weight is not None and weight <= 0:
            raise forms.ValidationError("Weight must be positive")
        return weight
