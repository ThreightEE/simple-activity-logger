import redis
import logging
from django.conf import settings

from typing import Any, Optional, Dict, Union


logger = logging.getLogger(__name__)

_connection_pool: Optional[redis.ConnectionPool] = None


def get_redis_connection() -> Optional[redis.Redis]:
    """
    Get connection to Redis from connection pool.
    Works with both config dictionary and URL.
    """
    global _connection_pool
    
    if _connection_pool is None:
        try:
            redis_config: Union[str, Dict[str, Any], None] = getattr(
                settings, 'CONSTANCE_REDIS_CONNECTION', None
            )
            
            if not redis_config:
                logger.error("CONSTANCE_REDIS_CONNECTION not defined")
                return None
            
            if isinstance(redis_config, dict):
                _connection_pool = redis.ConnectionPool(**redis_config)
            elif isinstance(redis_config, str):
                _connection_pool = redis.ConnectionPool.from_url(redis_config)
            else:
                return None
                
            logger.info(f"Created Redis connection pool with {redis_config}")
        
        except Exception as e:
            logger.error(f"Failed to create Redis connection pool: {e}",
                         exc_info=True)
            _connection_pool = None
            return None
    
    if _connection_pool is None:
        logger.error("Redis connection pool could not initialize")
        return None

    try:
        return redis.Redis(connection_pool=_connection_pool,
                           socket_timeout=5.0, socket_connect_timeout = 5.0)
    except Exception as e:
        logger.error(f"Failed to get Redis connection from pool: {e}",
                     exc_info=True)
        return None
