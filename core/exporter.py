import time
from prometheus_client import start_http_server, Counter, Histogram
import threading
from .monitoring import get_counter

TASKS_STARTED = Counter('celery_tasks_started', 'Number of activity processing tasks started')
TASKS_COMPLETED = Counter('celery_tasks_completed', 'Number of activity processing tasks completed')
TASKS_FAILED = Counter('celery_tasks_failed', 'Number of activity processing tasks failed')
CALORIES_BURNED = Counter('celery_calories_burned_total', 'Total calories burned')


def update_metrics_from_redis():
    last_values = {
        'tasks_started': 0,
        'tasks_completed': 0,
        'tasks_failed': 0,
        'total_calories': 0
    }
    
    while True:
        try:
            current = {
                'tasks_started': get_counter('tasks_started'),
                'tasks_completed': get_counter('tasks_completed'),
                'tasks_failed': get_counter('tasks_failed'),
                'total_calories': get_counter('total_calories')
            }
            
            if current['tasks_started'] > last_values['tasks_started']:
                TASKS_STARTED.inc(current['tasks_started'] - last_values['tasks_started'])
            
            if current['tasks_completed'] > last_values['tasks_completed']:
                TASKS_COMPLETED.inc(current['tasks_completed'] - last_values['tasks_completed'])
            
            if current['tasks_failed'] > last_values['tasks_failed']:
                TASKS_FAILED.inc(current['tasks_failed'] - last_values['tasks_failed'])
            
            if current['total_calories'] > last_values['total_calories']:
                CALORIES_BURNED.inc(current['total_calories'] - last_values['total_calories'])
            
            last_values = current.copy()
        except Exception as e:
            print(f"Error updating metrics: {e}")
        
        time.sleep(5)

def start_metrics_server(port=8001):
    try:
        start_http_server(port, addr='0.0.0.0')
        print(f"Prometheus metrics available at http://0.0.0.0:{port}/metrics")
        
        thread = threading.Thread(target=update_metrics_from_redis, daemon=True)
        thread.start()
    except Exception as e:
        print(f"ERROR starting metrics server: {e}")
