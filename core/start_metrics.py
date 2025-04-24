import os
import django
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'activity_logger.settings')
django.setup()

from core.exporter import start_metrics_server


if __name__ == "__main__":
    start_metrics_server(port=8001)
    while True:
        time.sleep(10)
        