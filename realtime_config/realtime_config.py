import threading
import os
import logging
from django.conf import settings
from constance import config as constance_config
import redis
import time

from .redis_client import get_redis_connection

from typing import Any, Union, Optional, Dict, Tuple


logger = logging.getLogger(__name__)

_local_cache: Dict[str, Any] = {}
_cache_lock: threading.Lock = threading.Lock()
# Fill in AppConfig.ready() with load_defaults()
_default_values: Dict[str, Any] = {}

_subscriber_thread: Optional[threading.Thread] = None
_subscriber_lock: threading.Lock = threading.Lock()

# Redis connection fail fast
_redis_available: bool = True
_last_redis_error_time: float = 0.0
_redis_status_lock = threading.Lock()


def load_defaults() -> None:
    """
    Load default config values locally.
    """
    global _default_values
    try:
        constance_defs: Dict[str, Tuple[Any, str, type]] = \
            getattr(settings, 'CONSTANCE_CONFIG', {})
        defaults: Dict[str, Any] = {key: definition[0] \
                                    for key, definition in constance_defs.items()}
        _default_values = defaults
        logger.info("Successfully loaded default config values")
    except Exception as e:
        logger.error("Failed to load default config values from settings. "
                     f"Error: {e}", exc_info=True)
        _default_values = {}


def get_config(key: str, default: Any = None) -> Any:
    """
    Get config value by key with caching.

    - Return local cache if there is any
    - Or try to get config from Redis:
     - save and return on success
     - otherwise, return default if given, or default from constance_config
    """
    global _redis_available, _last_redis_error_time

    current_pid: int = os.getpid()

    with _cache_lock:
        if key in _local_cache:
            logger.debug(f"Config {key} retrieved from local cache - "
                         f"{_local_cache[key]} (PID: {current_pid})")
            return _local_cache[key]

    logger.debug(f"Cache miss for config '{key}' (PID: {current_pid})")

    # Fail fast if going for Redis
    
    with _redis_status_lock:
        current_redis_available: bool = _redis_available
        current_last_error_time: float = _last_redis_error_time

    current_time: float = time.time()
    redis_retry_interval: float = getattr(settings, 'REDIS_RETRY_INTERVAL', 10.0)

    if not current_redis_available and \
       (current_time - current_last_error_time) < redis_retry_interval:
        logger.warning(f"Redis marked unavailable (PID: {current_pid}) - "
                       "not attempting connection for another "
                       f"{(redis_retry_interval - (current_time - current_last_error_time)):.1f}s")
    # Attempting to connect to Redis
    else:
        try:
            value: Any = getattr(constance_config, key)
            with _redis_status_lock:
                _redis_available = True

            with _cache_lock:
                _local_cache[key] = value
            logger.debug(f"Fetched config '{key}' from Redis and cached - {value} "
                         "(PID: {current_pid})")
            return value

        except redis.exceptions.RedisError as e:
            logger.warning(f"Redis operation failed for config '{key}' "
                           "(PID: {current_pid}). Error: {e}")
            with _redis_status_lock:
                _redis_available = False
                _last_redis_error_time = current_time

        except AttributeError:
            logger.error(f"Config '{key}' not found in Constance (PID: {current_pid})")

        except Exception as e:
            logger.error(f"Unexpected error getting config '{key}' "
                         "(PID: {current_pid}): {e}", exc_info=True)
    
    # Fallback

    logger.warning(f"Fallback for config '{key}'")
    if default is not None:
        logger.warning(f"Returning passed default {default}")
        return default
    
    if key in _default_values:
        preloaded_default: Any = _default_values.get(key)
        logger.warning(f"Returning preloaded default {preloaded_default}")
        return preloaded_default
    
    logger.error(f"No value found for config {key} (PID: {current_pid})")
    return None


def run_subscriber() -> None:
    """
    Run Redis Pub/Sub subscriber that listens for config changes.
    """
    logger.info("Redis Pub/Sub subscriber starting")
    channel_name: Optional[str] = getattr(settings, 'REDIS_PUB_SUB_CHANNEL', None)
    if not channel_name:
        logger.error("REDIS_PUB_SUB_CHANNEL is not defined")
        return

    logger.info(f"Subscriber listens to Redis channel '{channel_name}'")

    while True:
        redis_client: Optional[redis.Redis] = None
        pubsub: Optional[redis.client.PubSub] = None
        redis_retry_interval: float = getattr(settings, 'REDIS_RETRY_INTERVAL', 10.0)
                
        try:
            redis_client = get_redis_connection()
            if not redis_client:
                logger.warning("Subscriber failed to get Redis connection. "
                               f"Retrying in {redis_retry_interval} seconds...")
                time.sleep(redis_retry_interval)
                continue

            pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
            pubsub.subscribe(channel_name)
            logger.info(f"Subscribed to Redis channel: {channel_name}")

            for message in pubsub.listen():
                logger.debug(f"Subscriber received message: {message}")
                if message and message['type'] == 'message' and 'data' in message:
                    key = message.get('data')
                    if isinstance(key, bytes):
                        key = key.decode('utf-8')
                    else:
                        key = str(key) if key is not None else ""
                    
                    if key:
                        logger.info(f"Received update notification for key: {key}")
                        with _cache_lock:
                            # logger.debug(f"PID: {os.getpid()}, cache before invalidation: {_local_cache}")
                            removed_value: Any = _local_cache.pop(key, None)
                            logger.info(f"PID {os.getpid()}, removed value: {removed_value}")

                    if removed_value is not None:
                        logger.info(f"Invalidated cache for key: {key}")
                    else:
                        logger.debug(f"Key {key} not found in cache, nothing to invalidate")
                else:
                     logger.warning(f"Received unexpected message format from Pub/Sub: {message}")

        except redis.ConnectionError as e:
            logger.warning(f"Redis connection error in subscriber: {e}")
            time.sleep(redis_retry_interval)

        except Exception as e:
            logger.error(f"Unexpected error in Redis subscriber: {e}", exc_info=True)
            time.sleep(redis_retry_interval)

        finally:
            if pubsub:
                try:
                    if get_redis_connection() is not None:
                        pubsub.unsubscribe()
                        pubsub.close()
                        logger.debug("PubSub unsubscribed and connection closed.")
                except Exception as close_e:
                    logger.debug(f"Error during pubsub cleanup: {close_e}")


def start_subscriber_thread() -> None:
    """
    Start background thread for run_subscriber().
    """
    global _subscriber_thread

    with _subscriber_lock:
        if _subscriber_thread is None or not _subscriber_thread.is_alive():
            _subscriber_thread = threading.Thread(
                target=run_subscriber,
                # Don't wait for the thread to finish
                daemon=True,
                name="RedisConfigSubscriber"
            )
            _subscriber_thread.start()
            print(f"STARTED SUBSCRIBER THREAD IN PID: {os.getpid()}")
            logger.info(f"Started Redis Pub/Sub subscriber thread: {_subscriber_thread.name}")
        else:
            logger.info(f"Redis Pub/Sub subscriber thread '{_subscriber_thread.name}' is already running.")
