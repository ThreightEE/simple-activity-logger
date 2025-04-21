from django.db import models

from django.utils import timezone
from .enums import ActivityType, ProcessingStatus

# Create your models here.

class Activity(models.Model):
    """
    Log for single physical activity.
    """

    # Core Fields

    # from custom enum
    activity_type = models.CharField(
        max_length=10,
        choices=ActivityType.choices(),
        verbose_name="Type of Activity",
        help_text="Select the activity performed"
    )

    duration_minutes = models.PositiveIntegerField(
        verbose_name="Duration (minutes)",
        help_text="How long the activity lasted, in minutes"
    )

    # for calorie calculation
    weight_kg = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Weight (kg)",
        help_text="Your weight in kilograms (used for calorie calculations)"
    )

    notes = models.TextField(
        # Allow to be empty in forms
        blank=True,
        # Allow the DB column to store NULL
        null=True,
        verbose_name="Optional Notes",
        help_text="Additional notes about this activity"
    )

    # Timestamps

    created_at = models.DateTimeField(
        # Autoset when the object is first created
        auto_now_add=True,
        verbose_name="Logged At"
    )

    updated_at = models.DateTimeField(
        # Autoset every time the object is saved
        auto_now=True,
        verbose_name="Last Updated"
    )

    # Processing Info for Celery

    status = models.CharField(
        max_length=10,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
        # for faster querying
        db_index=True,
        verbose_name="Processing Status"
    )

    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Processed At",
        help_text="When the processing was finished"
    )

    calories_burned = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Calories Burned",
        help_text="Estimated calories burned during this activity"
    )

    # Task tracking
    celery_task_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        # Task might be retried or processing re-triggered
        unique=False,
        # Should be set by system, not manually edited
        editable=False,
        verbose_name="Celery Task ID",
        help_text="ID of task processing this activity."
    )

    # only set on failure
    error_message = models.TextField(
        null=True,
        blank=True,
        verbose_name="Error Message",
        help_text="Details about any errors if processing has failed"
    )

    class Meta:
        verbose_name = "Activity Log"
        verbose_name_plural = "Activity Logs"
        # Show newest activities first
        ordering = ['-created_at']

    # Helper Methods
    
    def __str__(self):
        """
        Return string representation.
        """
        return f"{ActivityType.get_label(self.activity_type)} for {self.duration_minutes} mins ({self.created_at.strftime('%Y-%m-%d')})"
    
    def calculate_calories(self):
        """
        Estimate calories burned using MET formula
        """
        if not self.weight_kg or not self.duration_minutes or self.duration_minutes <= 0:
            return None
        try:
            met_val = ActivityType.get_met(self.activity_type)
            duration_hrs = self.duration_minutes / 60.0
            calories = met_val * float(self.weight_kg) * duration_hrs
            return round(calories, 2)
        except (ValueError, TypeError, KeyError):
            return None
        
    def update_status(self, status, calories=None, error_msg=None):
        """
        Update processing status and related fields.
        Save changes. Handle error message.
        """

        # Validate input
        if status not in ProcessingStatus.values:
            raise ValueError(f"Invalid status: {status}")
        
        # List of fields to update
        update_fields_ = ['status', 'updated_at']
        self.status = status

        if status == ProcessingStatus.COMPLETED:
            # Record completion time
            self.processed_at = timezone.now()
            self.calories_burned = calories
            # Clear any previous error message
            self.error_message = None
            update_fields_.extend(['processed_at', 'calories_burned', 'error_message'])
        
        elif status == ProcessingStatus.FAILED:
            self.processed_at = timezone.now()
            # Clear potentially expired data
            self.calories_burned = None
            self.error_message = error_msg
            update_fields_.extend(['processed_at', 'calories_burned', 'error_message'])

        elif status == ProcessingStatus.PROCESSING:
            pass

        self.save(update_fields=update_fields_)

    @property
    def is_processed(self) -> bool:
        """
        Returns True only if the activity status is COMPLETED
        """
        return self.status == ProcessingStatus.COMPLETED
    
    @property
    def processing_time(self):
        """
        Returns total time in seconds between creation and processing completion.
        Returns None if not yet processed.
        """
        if self.processed_at and self.created_at:
            return (self.processed_at - self.created_at).total_seconds()
        return None
