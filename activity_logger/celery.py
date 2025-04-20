import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'activity_logger.settings')
app = Celery('activity_logger')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')