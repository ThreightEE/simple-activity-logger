import redis
from django.conf import settings

redis_client = redis.Redis.from_url(settings.CELERY_BROKER_URL)


def increment_counter(name):
    return redis_client.incr(f"counter:{name}")

def get_counter(name):
    value = redis_client.get(f"counter:{name}")
    return int(value) if value else 0

def increment_counter_by(name, amount):
    return redis_client.incrby(f"counter:{name}", amount)
