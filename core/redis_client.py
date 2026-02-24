"""Redis client with connection pooling for audit logging."""

from functools import lru_cache
from typing import Optional

import redis
from redis.connection import ConnectionPool

from core.settings import get_settings


@lru_cache(maxsize=1)
def get_redis_pool() -> ConnectionPool:
    """Get a singleton Redis connection pool."""
    settings = get_settings()
    return ConnectionPool(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_keepalive=True,
        socket_keepalive_options={
            1: 1,  # TCP_KEEPIDLE
            2: 1,  # TCP_KEEPINTVL
            3: 3,  # TCP_KEEPCNT
        },
    )


def get_redis_client() -> redis.Redis:
    """Get a Redis client from the connection pool."""
    return redis.Redis(connection_pool=get_redis_pool())


def test_redis_connection() -> bool:
    """Test if Redis is accessible."""
    try:
        client = get_redis_client()
        client.ping()
        return True
    except (redis.ConnectionError, redis.TimeoutError, Exception):
        return False


def set_audit_data(key: str, value: str, ttl: Optional[int] = None) -> bool:
    """
    Store audit data in Redis.

    Args:
        key: Redis key (e.g., "audit:exec_id:event_type:event_id")
        value: JSON string of the audit event
        ttl: Optional TTL in seconds for the key

    Returns:
        True if successful, False otherwise
    """
    try:
        client = get_redis_client()
        if ttl:
            client.setex(key, ttl, value)
        else:
            client.set(key, value)
        return True
    except Exception:
        return False


def get_audit_data(key: str) -> Optional[str]:
    """
    Retrieve audit data from Redis.

    Args:
        key: Redis key

    Returns:
        Value if found, None otherwise
    """
    try:
        client = get_redis_client()
        return client.get(key)
    except Exception:
        return None


def get_audit_keys(pattern: str) -> list[str]:
    """
    Get all keys matching a pattern.

    Args:
        pattern: Key pattern (e.g., "audit:exec_id:*")

    Returns:
        List of matching keys
    """
    try:
        client = get_redis_client()
        return client.keys(pattern)
    except Exception:
        return []


def delete_audit_keys(pattern: str) -> int:
    """
    Delete all keys matching a pattern.

    Args:
        pattern: Key pattern

    Returns:
        Number of keys deleted
    """
    try:
        client = get_redis_client()
        keys = client.keys(pattern)
        if keys:
            return client.delete(*keys)
        return 0
    except Exception:
        return 0
