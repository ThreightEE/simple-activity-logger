from django.apps import AppConfig
import sys
import logging
import os

from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


class ConfigAppConfig(AppConfig):
    default_auto_field: str = 'django.db.models.BigAutoField'
    name: str = 'realtime_config'

    _initialized_pids: Dict[int, bool] = {}

    def ready(self) -> None:
        """
        Initialize config defaults, signal connections, background threads for workers
        when app starts.
        """
        pid: int = os.getpid()
        logger.info(f"ConfigAppConfig.ready() CALLED in PID: {pid}")

        # Don't run init for basic manage.py commands
        management_commands: List[str] = [
            'makemigrations', 'migrate', 'collectstatic', 'check', 'shell', 'help',
            'createsuperuser', 'loaddata', 'dumpdata'
        ]
        command: Optional[str] = sys.argv[1] if len(sys.argv) > 1 else None
        is_management_command: bool = command in management_commands

        is_runserver_main_process: bool = os.environ.get('RUN_MAIN') == 'true'

        if is_management_command:
            logger.info(f"PID {pid}: Skipping Pub/Sub setup "
                        f"for management command '{command}'")
            return

        if is_runserver_main_process:
            logger.info(f"PID {pid}: Skipping Pub/Sub setup "
                        "for runserver reloader process")
            return
        
        # Don't run init for start_metrics
        is_metrics_script = 'start_metrics.py' in sys.argv[0]
        if is_metrics_script:
            logger.info(f"PID {pid}: Skipping Pub/Sub setup "
                        "for metrics utility")
            return
        
        if pid in self.__class__._initialized_pids:
            logger.info(f"PID {pid}: Worker already initialized, skipping")
            return

        try:
            from . import realtime_config
            from . import signals
            from constance.signals import config_updated

            realtime_config.load_defaults()
            logger.info(f"PID {pid}: Loaded constance config defaults")

            config_updated.connect(signals.config_updated_handler,
                                   dispatch_uid=f"config_updated_handler_{pid}")
            logger.info(f"PID {pid}: Successfully connected "
                        "'config_updated' signal to 'config_updated_handler'")

            logger.info(f"PID {pid}: Starting Redis Pub/Sub subscriber")
            realtime_config.start_subscriber_thread()

            self.__class__._initialized_pids[pid] = True
            logger.info(f"PID {pid}: Initialization COMPLETE")

        except Exception as e:
            logger.error(f"PID {pid}: Error in ConfigAppConfig.ready(). "
                         f"Error: {e}", exc_info=True)
