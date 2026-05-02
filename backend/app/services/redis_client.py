import json
import logging
from typing import Optional

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

PUBSUB_CHANNEL = "chat_events"

_client: Optional[aioredis.Redis] = None


async def _get_client() -> Optional[aioredis.Redis]:
    global _client
    if _client is not None:
        try:
            await _client.ping()
            return _client
        except Exception:
            _client = None

    try:
        _client = aioredis.from_url(settings.redis_url, decode_responses=True)
        await _client.ping()
        return _client
    except Exception as e:
        logger.warning("Redis unavailable: %s", e)
        _client = None
        return None


async def publish_event(event: dict) -> bool:
    client = await _get_client()
    if client is None:
        return False
    try:
        await client.publish(PUBSUB_CHANNEL, json.dumps(event))
        return True
    except Exception as e:
        logger.warning("Redis publish failed: %s", e)
        return False


async def close() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
