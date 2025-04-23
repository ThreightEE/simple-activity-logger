import logging
import time
from celery import shared_task
from django.utils import timezone
from .models import Activity
from .enums import ProcessingStatus

logger = logging.getLogger(__name__)
# Processing delay in seconds
delay_time = 3
# Time before retrying on error
retry_time = 60

@shared_task(bind=True, max_retries=3)
def process_activity(self, activity_id):
    """
    Calculate calories burned and update status.
    ! Delay to simulate processing.
    Retry if fails.
    """

    try:
        activity = Activity.objects.get(id=activity_id)
    # Will not retry the task if activity doesn't exist
    except Activity.DoesNotExist:
        logger.error(f"Activity {activity_id} not found")
        return False

    logger.info(f"Starting processing activity {activity_id}")
    try:
        activity.update_status(ProcessingStatus.PROCESSING)
        activity.celery_task_id = self.request.id
        activity.save(update_fields=['celery_task_id'])
        
        # Delay happens here ! ! !
        processing_time = delay_time
        logger.info(f"Got the activity {activity_id}, processing for {processing_time}s")
        time.sleep(processing_time)
        
        calories = activity.calculate_calories()
        if calories is None:
            raise ValueError("Failed to calculate calories")
        
        activity.update_status(ProcessingStatus.COMPLETED, calories=calories)
        logger.info(f"Successfully processed activity {activity_id}, burned {calories} calories")
        return True
    
    except Exception as exc:
        logger.exception(f"Error processing activity {activity_id}: {str(exc)}")
        
        # Update status if possible
        try:
            activity = Activity.objects.get(id=activity_id)
            activity.update_status(
                ProcessingStatus.FAILED, 
                error_msg=f"Processing error: {str(exc)}"
            )
        except Exception:
            pass
        
        # Retry with respect to max_retries
        raise self.retry(exc=exc, countdown=retry_time)
