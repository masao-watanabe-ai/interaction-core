import asyncio
import json
import logging

import redis.asyncio as aioredis

from app.config import settings
from app.services.redis_client import PUBSUB_CHANNEL
from app.services.websocket_service import manager

logger = logging.getLogger(__name__)


async def redis_subscriber_loop() -> None:
    while True:
        r: aioredis.Redis | None = None
        try:
            r = aioredis.from_url(settings.redis_url, decode_responses=True)
            pubsub = r.pubsub()
            await pubsub.subscribe(PUBSUB_CHANNEL)
            logger.info("Redis subscriber connected, listening on '%s'", PUBSUB_CHANNEL)
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        event = json.loads(message["data"])
                        await manager.broadcast_local(event)
                    except Exception as e:
                        logger.warning("Failed to process Redis message: %s", e)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning("Redis subscriber error, retrying in 3s: %s", e)
        finally:
            if r is not None:
                try:
                    await r.aclose()
                except Exception:
                    pass
        await asyncio.sleep(3)
