import logging
import redis
from django.conf import settings
from .redis_client import get_redis_connection
from .models import ConfigChangeLog

from typing import Any, Optional

logger = logging.getLogger(__name__)


def config_updated_handler(
        sender: Any,
        key: str,
        old_value: Optional[Any],
        new_value: Any,
        **kwargs: Any
    ) -> None:
    """
    Call when constance config updates. Publish key to Redis Pub/Sub channel.
    + Log change to database.
    """
    logger.info(f"Signal config_updated received for key='{key}'. "
                f"Old='{old_value}', New='{new_value}'")

    # Logging to DB
    try:
        old: Optional[str] = str(old_value) if old_value is not None else None
        new: str = str(new_value) if new_value is not None else ""

        ConfigChangeLog.objects.create(
            key=key,
            old_value=old,
            new_value=new
        )
        logger.info(f"Logged change for config {key} to DB")
    except Exception as e:
        logger.error(f"Failed to log change for config {key}. Error: {e}",
                     exc_info=True)
    
    channel_name: Optional[str] = getattr(settings, 'REDIS_PUB_SUB_CHANNEL', None)
    if not channel_name:
        logger.error("REDIS_PUB_SUB_CHANNEL not defined")
        return

    redis_client: Optional[redis.Redis] = get_redis_connection()
    if not redis_client:
        logger.error("Failed to get Redis connection to publish config change")
        return

    try:
        got_msg_count: int = redis_client.publish(channel_name, key)
        logger.info(f"Published key='{key}' to Redis channel '{channel_name}'. "
                    f"Subscribers notified: {got_msg_count}")

    except redis.exceptions.RedisError as e:
        logger.error(f"Redis error during publishing for key='{key}'. Error: {e}",
                     exc_info=True)
        
    except Exception as e:
        logger.error(f"Unexpected error during publishing for key='{key}'. Error: {e}",
                     exc_info=True)
