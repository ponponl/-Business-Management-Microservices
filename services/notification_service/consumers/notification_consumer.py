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
    event_type = event_data.get("event_type") or event_data.get("event_name")
    
    # Nếu payload được bọc trong field "payload", lấy nó. Nếu không, toàn bộ event_data chính là payload
    payload = event_data.get("payload", event_data)
    if isinstance(payload, str):
        payload = json.loads(payload)
        
    logger.info(f"Received event {event_type} from {topic}")

    contract_number = payload.get("contract_number", "Unknown")
    title = ""
    message = ""

    if event_type == "CONTRACT_CREATED":
        title = "Hợp đồng mới được tạo"
        message = f"Hợp đồng {contract_number} đã được tạo thành công."
    elif event_type == "CONTRACT_UPDATED":
        title = "Hợp đồng được cập nhật"
        message = f"Hợp đồng {contract_number} đã được cập nhật."
    elif event_type == "CONTRACT_SUBMITTED":
        title = "Hợp đồng chờ duyệt (Manager)"
        message = f"Hợp đồng {contract_number} đã được gửi để Manager duyệt."
    elif event_type == "CONTRACT_MANAGER_REVIEW_STARTED":
        title = "Quá trình duyệt bắt đầu (Manager)"
        message = f"Manager đang xem xét hợp đồng {contract_number}."
    elif event_type == "CONTRACT_MANAGER_APPROVED":
        title = "Hợp đồng chờ duyệt (Director)"
        message = f"Hợp đồng {contract_number} đã được Manager duyệt, đang chờ Director duyệt."
    elif event_type == "CONTRACT_DIRECTOR_REVIEW_STARTED":
        title = "Quá trình duyệt bắt đầu (Director)"
        message = f"Director đang xem xét hợp đồng {contract_number}."
    elif event_type == "CONTRACT_DIRECTOR_APPROVED":
        title = "Hợp đồng đã được phê duyệt"
        message = f"Hợp đồng {contract_number} đã được phê duyệt hoàn toàn."
    elif event_type in ["CONTRACT_MANAGER_REJECTED", "CONTRACT_DIRECTOR_REJECTED"]:
        reason = payload.get("comment", "")
        role = "Manager" if "MANAGER" in event_type else "Director"
        title = f"Hợp đồng bị từ chối ({role})"
        message = f"Hợp đồng {contract_number} bị từ chối. Lý do: {reason}"
    elif event_type in ["CONTRACT_MANAGER_REVISION_REQUESTED", "CONTRACT_DIRECTOR_REVISION_REQUESTED"]:
        role = "Manager" if "MANAGER" in event_type else "Director"
        title = f"Yêu cầu chỉnh sửa hợp đồng ({role})"
        message = f"Hợp đồng {contract_number} cần được {role} xem xét và chỉnh sửa."
    elif event_type == "CONTRACT_MANAGER_SEND_REVISION":
        title = "Yêu cầu chỉnh sửa hợp đồng (Staff)"
        message = f"Hợp đồng {contract_number} cần được Staff chỉnh sửa lại."
    elif event_type == "CONTRACT_RENEWED":
        title = "Hợp đồng được gia hạn"
        message = f"Hợp đồng {contract_number} đã được gia hạn."
    elif event_type == "CONTRACT_CANCELLED":
        title = "Hợp đồng bị hủy"
        message = f"Hợp đồng {contract_number} đã bị hủy."
    elif event_type == "CONTRACT_ACTIVATED":
        title = "Hợp đồng có hiệu lực"
        message = f"Hợp đồng {contract_number} hiện đã có hiệu lực."
    elif event_type == "CONTRACT_EXPIRED":
        title = "Hợp đồng hết hạn"
        message = f"Hợp đồng {contract_number} đã hết hạn."
    else:
        logger.info(f"Ignored event type {event_type}")
        return

    # Thông báo hiển thị cho cả 3 roles (Staff=1, Manager=2, Director=3)
    user_ids = [1, 2, 3]
    for uid in user_ids:
        unique_event_id = f"{event_id}-{uid}"
        
        # 1. Kiểm tra Idempotency cho từng user
        existing = db.query(Notification).filter(Notification.event_id == unique_event_id).first()
        if existing:
            logger.info(f"Event {unique_event_id} already processed (Idempotency). Skipping.")
            continue
            
        notif = Notification(
            user_id=uid,
            title=title,
            message=message,
            event_type=event_type,
            reference_id=contract_number,
            event_id=unique_event_id
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
