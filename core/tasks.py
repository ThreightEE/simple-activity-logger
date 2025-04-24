import logging
import time
from celery import shared_task
from django.utils import timezone
from .models import Activity
from .enums import ProcessingStatus

from .monitoring import increment_counter, increment_counter_by


logger = logging.getLogger(__name__)

# Processing delay in seconds
delay_time = 5
max_retries_ = 3
# Time before retrying on error
retry_time = 30


@shared_task(
    bind=True,
    max_retries=max_retries_,
    default_retry_delay=retry_time,
    ignore_result=True
)
def process_activity(self, activity_id):
    """
    Calculate calories burned and update status.
    ! Delay to simulate processing.
    Retry if fails.
    """

    increment_counter('tasks_started')

    # Start timing for performance monitoring
    start_time = time.time()

    try:
        activity = Activity.objects.get(id=activity_id)
    # Will not retry the task if activity doesn't exist
    except Activity.DoesNotExist:
        logger.error(f"Activity {activity_id} not found")
        
        retry_delay = retry_time * (2 ** self.request.retries)
        raise self.retry(countdown=retry_delay, exc=Exception(f"Activity {activity_id} not yet in database"))

    activity.update_status(ProcessingStatus.PROCESSING)
    logger.info(f"Starting processing activity {activity_id}")
    
    try:
        activity.celery_task_id = self.request.id
        activity.save(update_fields=['celery_task_id'])
        
        # Delay happens here ! ! !
        logger.info(f"Got the activity {activity_id}, processing for {delay_time}s")
        time.sleep(delay_time)
        
        calories = activity.calculate_calories()
        if calories is None:
            raise ValueError("Failed to calculate calories")
        
        activity.update_status(ProcessingStatus.COMPLETED, calories=calories)

        duration = time.time() - start_time
        logger.info(
            f"Successfully processed activity {activity_id}: burned {calories} calories"
            f" - in {duration:.2f}s"
        )

        increment_counter('tasks_completed')
        calories_int = int(float(calories))
        increment_counter_by('total_calories', calories_int)

        return True
    
    except Exception as exc:
        duration = time.time() - start_time
        logger.exception(
            f"Error processing activity {activity_id} after {duration:.2f}s: {str(exc)}"
        )

        increment_counter('tasks_failed')
        
        # Update status to FAILED if possible
        try:
            activity.update_status(
                ProcessingStatus.FAILED, 
                error_msg=f"Processing error: {str(exc)}"
            )
        except Exception as update_exc:
            logger.exception(
                f"Failed to update failed activity {activity_id} status: {str(update_exc)}"
            )
        
        # Retry with respect to max_retries
        raise self.retry(exc=exc)
    

@shared_task
def requeue_pending_activities():    
    cutoff = timezone.now() - timezone.timedelta(minutes=1)

    pending_activities = Activity.objects.filter(
        status=ProcessingStatus.PENDING,
        created_at__lte=cutoff
    )

    failed_activities = Activity.objects.filter(
        status=ProcessingStatus.FAILED,
    )
    
    pending_count = pending_activities.count()
    failed_count = failed_activities.count()
    
    logger.info(f"Found {pending_count} activities stuck in PENDING status")
    logger.info(f"Found {failed_count} FAILED activities to retry")
    
    for activity in pending_activities:
        try:
            result = process_activity.delay(activity.id)
            activity.celery_task_id = result.id
            activity.save(update_fields=['celery_task_id'])
            logger.info(f"Requeued activity {activity.id} with task {result.id}")
        
        except Exception as e:
            logger.error(f"Failed to requeue activity {activity.id}: {str(e)}")

    for activity in failed_activities:
        try:
            result = process_activity.delay(activity.id)
            activity.status = ProcessingStatus.PENDING
            activity.celery_task_id = result.id
            activity.error_message = f"Retrying after {activity.error_message}"
            activity.save(update_fields=['status', 'celery_task_id', 'error_message'])
            
            logger.info(f"Retrying FAILED activity {activity.id} with new task {result.id}")
        except Exception as e:
            logger.error(f"Failed to retry FAILED activity {activity.id}: {str(e)}")

    total_requeued = pending_count + failed_count
    if total_requeued > 0:
        increment_counter('tasks_requeued', total_requeued)
    
    return f"Requeued {pending_count} pending and {failed_count} failed activities"
