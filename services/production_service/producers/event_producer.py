from core.kafka import kafka_producer
import logging

logger = logging.getLogger(__name__)

async def publish_volume_recorded(volume_id: int, period_key: str):
    event_data = {
        "event_name": "VOLUME_RECORDED",
        "volume_id": volume_id,
        "period_key": period_key
    }
    await kafka_producer.send_event("volume.events", event_data)
    logger.info(f"Published VOLUME_RECORDED for volume {volume_id}")

async def publish_period_locked(period_key: str):
    event_data = {
        "event_name": "VOLUME_PERIOD_LOCKED",
        "period_key": period_key
    }
    await kafka_producer.send_event("period.events", event_data)
    logger.info(f"Published VOLUME_PERIOD_LOCKED for period {period_key}")

async def publish_period_unlocked(period_key: str):
    event_data = {
        "event_name": "VOLUME_PERIOD_UNLOCKED",
        "period_key": period_key
    }
    await kafka_producer.send_event("period.events", event_data)
    logger.info(f"Published VOLUME_PERIOD_UNLOCKED for period {period_key}")
