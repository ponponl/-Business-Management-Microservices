import redis.asyncio as aioredis
from app.core.config import settings

redis_client = None

async def init_redis():
    global redis_client
    # Khởi tạo kết nối qua REDIS_URL
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()