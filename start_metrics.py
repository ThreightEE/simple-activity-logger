import os
import django
import time

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'activity_logger.settings')
django.setup()

# Import after Django setup
from core.exporter import start_metrics_server

if __name__ == "__main__":
    # Start metrics server
    start_metrics_server(port=8001)
    
    # Keep the script running
    while True:
        time.sleep(10)
        