import asyncio
import logging
import json
from core.database import SessionLocal
from models.operation import OperationOutboxEvent
from producers.event_producer import publish_volume_recorded, publish_period_locked, publish_period_unlocked

logger = logging.getLogger(__name__)

async def process_outbox_events():
    db = SessionLocal()
    try:
        # Lấy tối đa 50 events đang PENDING để xử lý
        pending_events = db.query(OperationOutboxEvent).filter(OperationOutboxEvent.status == "PENDING").limit(50).all()
        
        if not pending_events:
            return

        logger.info(f"Outbox Relay: Found {len(pending_events)} pending events.")
        
        for event in pending_events:
            try:
                payload = json.loads(event.payload)
                
                # Gửi sự kiện dựa trên event_type
                if event.event_type == "VOLUME_RECORDED":
                    await publish_volume_recorded(payload["volume_id"], payload["period_key"])
                elif event.event_type == "VOLUME_PERIOD_LOCKED":
                    await publish_period_locked(payload["period_key"])
                elif event.event_type == "VOLUME_PERIOD_UNLOCKED":
                    await publish_period_unlocked(payload["period_key"])
                else:
                    logger.warning(f"Outbox Relay: Unknown event type {event.event_type}")
                    continue
                
                # Nếu gửi thành công thì cập nhật PUBLISHED
                event.status = "PUBLISHED"
                db.commit()
                logger.info(f"Outbox Relay: Successfully published event {event.id}")
                
            except Exception as e:
                # Bỏ qua lỗi và để lại PENDING cho lần chạy sau
                db.rollback()
                logger.error(f"Outbox Relay: Failed to publish event {event.id}: {e}")
                
    except Exception as e:
        logger.error(f"Outbox Relay error: {e}")
    finally:
        db.close()

async def start_outbox_relay(interval_seconds: int = 60):
    """Vòng lặp chạy ngầm định kỳ quét bảng outbox"""
    logger.info(f"Starting Outbox Relay Publisher. Interval: {interval_seconds}s")
    while True:
        try:
            await process_outbox_events()
        except Exception as e:
            logger.error(f"Unexpected error in outbox relay loop: {e}")
        
        # Ngủ một khoảng thời gian trước khi quét lần tiếp theo
        await asyncio.sleep(interval_seconds)
