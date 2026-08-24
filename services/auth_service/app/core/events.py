import json
import logging
import os
from typing import Optional, Dict, Any
from aiokafka import AIOKafkaProducer
from app.core.config import settings

logger = logging.getLogger("auth_events")

KAFKA_BOOTSTRAP_SERVERS = getattr(
    settings,
    "KAFKA_BOOTSTRAP_SERVERS",
    os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092"),
)

kafka_producer: AIOKafkaProducer = None


async def init_kafka():
    """Khởi tạo Kafka Producer toàn cục khi FastAPI startup"""
    global kafka_producer
    try:
        kafka_producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS
        )
        await kafka_producer.start()
        logger.info(
            f"Auth Service Kafka Producer initialized successfully ({KAFKA_BOOTSTRAP_SERVERS})."
        )
    except Exception as e:
        logger.error(f"Failed to initialize Auth Service Kafka Producer: {e}")


async def stop_kafka():
    """Đóng kết nối Kafka Producer khi FastAPI shutdown"""
    global kafka_producer
    if kafka_producer:
        try:
            await kafka_producer.stop()
            logger.info("Auth Service Kafka Producer stopped gracefully.")
        except Exception as e:
            logger.error(f"Error stopping Auth Service Kafka Producer: {e}")


async def _get_or_init_producer():
    """Hàm nội bộ đảm bảo luôn có Producer để gửi message"""
    global kafka_producer
    if kafka_producer is None:
        logger.warning("Kafka Producer is None, attempting ad-hoc initialization...")
        await init_kafka()
    return kafka_producer


async def publish_user_login_event(
    user_data: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    **kwargs
):
    """
    Bắn event khi user đăng nhập thành công.
    Hỗ trợ cả 2 cách truyền:
      1. publish_user_login_event({"id": "123", "username": "admin"})
      2. publish_user_login_event(user_id="123", username="admin")
    """
    producer = await _get_or_init_producer()
    if not producer:
        logger.error("[Kafka Error] Unable to acquire Kafka Producer for login event!")
        return

    # Tổng hợp thông tin từ dict hoặc kwargs
    if user_data is None:
        user_data = {}

    final_user_id = str(
        user_id
        or user_data.get("id")
        or user_data.get("user_id")
        or kwargs.get("id", "")
    ).strip()

    final_username = str(
        username
        or user_data.get("username")
        or user_data.get("email")
        or kwargs.get("email", "")
    ).strip()

    try:
        payload_data = {
            "event_name": "USER_LOGGED_IN",
            "user_id": final_user_id,
            "username": final_username,
        }
        payload = json.dumps(payload_data).encode("utf-8")
        await producer.send_and_wait("user-events", payload)
        logger.info(
            f"[Kafka Producer] Published USER_LOGGED_IN for {payload_data['username']}"
        )
    except Exception as e:
        logger.error(f"[Kafka Producer Error] Failed to publish login event: {e}")


async def publish_user_sync_event(
    user_data: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    **kwargs
):
    """
    Bắn event đồng bộ thông tin user.
    Hỗ trợ linh hoạt cả truyền dict và truyền kwargs.
    """
    producer = await _get_or_init_producer()
    if not producer:
        logger.error("[Kafka Error] Unable to acquire Kafka Producer for sync event!")
        return

    if user_data is None:
        user_data = {}

    final_user_id = str(
        user_id
        or user_data.get("id")
        or user_data.get("user_id")
        or kwargs.get("id", "")
    ).strip()

    final_username = str(
        username
        or user_data.get("username")
        or user_data.get("email")
        or kwargs.get("email", "")
    ).strip()

    try:
        payload_data = {
            "event_name": "USER_SYNC",
            "user_id": final_user_id,
            "username": final_username,
        }
        payload = json.dumps(payload_data).encode("utf-8")
        await producer.send_and_wait("user-events", payload)
        logger.info(
            f"[Kafka Producer] Published USER_SYNC for {payload_data['username']}"
        )
    except Exception as e:
        logger.error(f"[Kafka Producer Error] Failed to publish sync event: {e}")