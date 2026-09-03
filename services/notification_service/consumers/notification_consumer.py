import json
import logging
from aiokafka import AIOKafkaConsumer
from core.config import settings
from core.database import SessionLocal
from models.notification import Notification

logger = logging.getLogger(__name__)

# Các topic cần lắng nghe (chỉ lấy từ contract_service)
KAFKA_TOPICS = ["contract.events"]
consumer = None

def process_event(topic: str, event_data: dict, db, event_id: str):
    """
    Xử lý event từ Kafka và tạo thông báo (Notification) tương ứng.
    Tùy vào event_type mà tạo nội dung thông báo khác nhau.
    """
    # 1. Kiểm tra Idempotency (Tránh nhận 1 thông báo 2 lần)
    existing = db.query(Notification).filter(Notification.event_id == event_id).first()
    if existing:
        logger.info(f"Event {event_id} already processed (Idempotency). Skipping.")
        return
    event_type = event_data.get("event_type") or event_data.get("event_name")
    
    # Nếu payload được bọc trong field "payload", lấy nó. Nếu không, toàn bộ event_data chính là payload
    payload = event_data.get("payload", event_data)
    if isinstance(payload, str):
        payload = json.loads(payload)
        
    logger.info(f"Received event {event_type} from {topic}")

    # VD: Xử lý sự kiện từ contract_service
    if event_type == "CONTRACT_CREATED":
        user_id = payload.get("created_by", 1)
        contract_number = payload.get("contract_number", "Unknown")
        notif = Notification(
            user_id=user_id,
            title="Hợp đồng mới được tạo",
            message=f"Hợp đồng {contract_number} đã được tạo thành công.",
            event_type=event_type,
            reference_id=contract_number,
            event_id=event_id
        )
        db.add(notif)

    elif event_type == "CONTRACT_APPROVED":
        # Tìm user_id phù hợp (người tạo hợp đồng hoặc manager). Tạm hardcode 1 để demo
        user_id = payload.get("created_by", 1)
        contract_number = payload.get("contract_number", "Unknown")
        notif = Notification(
            user_id=user_id,
            title="Hợp đồng đã được duyệt",
            message=f"Hợp đồng {contract_number} đã được duyệt thành công.",
            event_type=event_type,
            reference_id=contract_number,
            event_id=event_id
        )
        db.add(notif)

    elif event_type == "CONTRACT_REJECTED":
        user_id = payload.get("created_by", 1)
        contract_number = payload.get("contract_number", "Unknown")
        reason = payload.get("comment", "")
        notif = Notification(
            user_id=user_id,
            title="Hợp đồng bị từ chối",
            message=f"Hợp đồng {contract_number} bị từ chối. Lý do: {reason}",
            event_type=event_type,
            reference_id=contract_number,
            event_id=event_id
        )
        db.add(notif)

        
    db.commit()

async def start_consumer():
    global consumer
    try:
        consumer = AIOKafkaConsumer(
            *KAFKA_TOPICS,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id="notification_group",
            value_deserializer=lambda x: json.loads(x.decode("utf-8")),
            enable_auto_commit=False # 2. Tắt Auto Commit để xử lý "Event bị mất"
        )
        await consumer.start()
        logger.info("Notification Consumer started and listening...")
        
        async for msg in consumer:
            db = SessionLocal()
            try:
                # Tạo event_id duy nhất từ thông tin Kafka (topic, partition, offset)
                event_id = f"{msg.topic}-{msg.partition}-{msg.offset}"
                process_event(msg.topic, msg.value, db, event_id)
                
                # 3. Chạy thành công, lưu DB xong mới báo cho Kafka (Manual Commit)
                await consumer.commit()
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                # Không commit -> Kafka sẽ tự động gửi lại (Retry)
            finally:
                db.close()
                
    except Exception as e:
        logger.error(f"Kafka Consumer failed to start: {e}")

async def stop_consumer():
    global consumer
    if consumer:
        await consumer.stop()
        logger.info("Notification Consumer stopped.")
