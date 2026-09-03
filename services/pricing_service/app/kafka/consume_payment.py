import asyncio
import json
import logging
from datetime import datetime
from uuid import UUID
from typing import Optional

from aiokafka import AIOKafkaConsumer
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.pricing import PriceListUsageLog, PriceListVersion

logger = logging.getLogger(__name__)


def parse_datetime(dt_str: Optional[str]) -> datetime:
    """Hàm hỗ trợ parse chuỗi Datetime ISO linh hoạt."""
    if not dt_str:
        return datetime.utcnow()
    try:
        # Thay thế chữ Z bằng múi giờ UTC tiêu chuẩn
        clean_str = str(dt_str).replace("Z", "+00:00")
        return datetime.fromisoformat(clean_str)
    except Exception:
        return datetime.utcnow()


def save_usage_log(data: dict):
    """
    Hàm xử lý và lưu/cập nhật nhật ký áp dụng bảng giá vào CSDL.
    """
    db: Session = SessionLocal()
    try:
        payment_board_id = data.get("id") or data.get("paymentBoardId")
        version_id_raw = data.get("priceListVersionId") or data.get("versionId")
        price_list_id_raw = data.get("priceListId")

        if not payment_board_id:
            logger.warning("Kafka Event thiếu payment_board_id (id), bỏ qua xử lý.")
            return

        # Parse UUID
        version_id = UUID(str(version_id_raw)) if version_id_raw else None
        price_list_id = UUID(str(price_list_id_raw)) if price_list_id_raw else None

        # 1. Tự động suy ra price_list_id nếu chưa có trong payload
        if version_id and not price_list_id:
            version_obj = db.query(PriceListVersion).filter(PriceListVersion.id == version_id).first()
            if version_obj:
                price_list_id = version_obj.price_list_id

        applied_at = parse_datetime(data.get("occurredAt") or data.get("appliedAt"))

        # 2. Kiểm tra tính trùng lặp (Idempotency) theo payment_board_id
        existing_log = (
            db.query(PriceListUsageLog)
            .filter(PriceListUsageLog.payment_board_id == payment_board_id)
            .first()
        )

        if existing_log:
            # Nếu đã tồn tại -> Tiến hành cập nhật thông tin mới nhất
            existing_log.status = data.get("status", existing_log.status)
            existing_log.total_amount = data.get("totalAmount", existing_log.total_amount)
            existing_log.issued_by = data.get("issuedBy", existing_log.issued_by)
            if version_id:
                existing_log.price_list_version_id = version_id
            if price_list_id:
                existing_log.price_list_id = price_list_id
            
            db.commit()
            logger.info(f"Updated PriceListUsageLog for payment_id: {payment_board_id}")
        else:
            # Nếu chưa có -> Tạo mới bản ghi
            usage_log = PriceListUsageLog(
                price_list_id=price_list_id,
                price_list_version_id=version_id,
                payment_board_id=payment_board_id,
                payment_code=data.get("code") or data.get("paymentCode"),
                status=data.get("status", "CALCULATED"),
                total_amount=data.get("totalAmount"),
                customer_id=data.get("customerId"),
                contract_id=data.get("contractId"),
                service_item_id=data.get("serviceItemId"),
                issued_by=data.get("issuedBy"),
                applied_at=applied_at,
            )
            db.add(usage_log)
            db.commit()
            logger.info(f"Saved new PriceListUsageLog for payment_id: {payment_board_id}")

    except Exception as e:
        db.rollback()
        logger.error(f"Error saving/updating usage log from Kafka: {e}", exc_info=True)
    finally:
        db.close()


async def consume_payment_events():
    """
    Consumer Kafka lắng nghe các sự kiện phát hành/áp dụng bản kê từ Payment Service.
    """
    consumer = AIOKafkaConsumer(
        "payment.issued",
        bootstrap_servers="kafka:29092",
        group_id="pricing-payment-issued",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )

    await consumer.start()
    logger.info("Kafka Consumer started, listening on topic 'payment.issued'...")
    try:
        async for msg in consumer:
            payload = msg.value
            event_type = payload.get("event") or payload.get("eventType")
            
            # Xử lý các sự kiện phát hành hoặc tính toán lại bản kê
            if event_type in ["PAYMENT_ISSUED", "PAYMENT_BOARD_CREATED", "PAYMENT_BOARD_UPDATED"]:
                await asyncio.to_thread(save_usage_log, payload)
            else:
                # Fallback: Nếu không có trường event nhưng chứa thông tin payment board
                if "priceListVersionId" in payload or "versionId" in payload:
                    await asyncio.to_thread(save_usage_log, payload)
                    
    except Exception as e:
        logger.error(f"Kafka consumer runtime error: {e}")
    finally:
        await consumer.stop()
        logger.info("Kafka Consumer stopped.")