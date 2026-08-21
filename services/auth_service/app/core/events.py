import json
import logging
from datetime import datetime, timezone
from aiokafka import AIOKafkaProducer
from app.core.config import settings

logger = logging.getLogger("auth_events")
kafka_producer: AIOKafkaProducer = None

async def init_kafka():
    global kafka_producer
    try:
        kafka_producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )
        await kafka_producer.start()
        logger.info("Kafka Producer started successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Kafka Producer: {e}")
        kafka_producer = None

async def stop_kafka():
    global kafka_producer
    if kafka_producer:
        await kafka_producer.stop()
        logger.info("Kafka Producer stopped.")

async def publish_user_login_event(user_id: str, role: str):
    if kafka_producer:
        payload = {
            "event_name": "USER_LOGGED_IN",
            "user_id": user_id,
            "role": role,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        try:
            await kafka_producer.send_and_wait("auth-events", payload)
        except Exception as e:
            logger.error(f"Failed to publish Kafka event: {e}")