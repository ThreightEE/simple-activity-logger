import os
import logging
from celery.signals import worker_process_init

logger = logging.getLogger(__name__)
_worker_initialized_pids = {}

@worker_process_init.connect(weak=False)
def init_worker_process(sender=None, **kwargs):
    """
    Initialize celery worker with real-time config subscriber
    """
    pid: int = os.getpid()
    if pid in _worker_initialized_pids:
        logger.info(f"CELERY_WORKER_INIT PID {pid}: Already initialized, skipping.")
        return
    
    from . import realtime_config
    realtime_config.load_defaults()
    realtime_config.start_subscriber_thread()
    
    _worker_initialized_pids[pid] = True
    print(f"Celery worker {pid} initialized with realtime_config")
