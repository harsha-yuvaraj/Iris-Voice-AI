import json
import redis.asyncio as aredis
from typing import List
from decouple import config

redis_client = None

async def get_redis_client():
    """
    Lazily initialize and return a Redis client connection pool.
    """
    global redis_client
    if redis_client is None:
        redis_client = await aredis.from_url(config('REDIS_URL'), decode_responses=True)
    return redis_client

async def update_conversation_context(key: str, role: str, msg: str) -> None:
    client = await get_redis_client()

    data = await client.get(key)
    data = json.loads(data) if data else []
    
    data.append({"role": role, "content": msg})

    await client.set(key, json.dumps(data), ex=7200)
    return data


async def get_conversation_context(key: str) -> List[dict]:
    client = await get_redis_client()
    data = await client.get(key)
    if not data:
        return []
    
    return json.loads(data)

async def remove_conversation_context(key: str) -> None:
    client = await get_redis_client()
    await client.delete(key)
