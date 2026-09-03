import asyncio
import json
import logging
import os
from datetime import datetime
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import GroupCoordinatorNotAvailableError, KafkaConnectionError
from app.db.session import SessionLocal
from app.models.pricing import UserCache, PriceListUsageLog

logger = logging.getLogger("pricing_events")

# Global Consumer Variables
kafka_consumer: AIOKafkaConsumer = None
payment_consumer: AIOKafkaConsumer = None

consumer_task: asyncio.Task = None
payment_consumer_task: asyncio.Task = None

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")


# 1. USER EVENTS CONSUMER (CODE CŨ GIỮ NGUYÊN)
async def consume_user_events():
    global kafka_consumer
    
    # Vòng lặp Retry cho đến khi Kafka sẵn sàng
    while True:
        try:
            kafka_consumer = AIOKafkaConsumer(
                "user-events",
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                group_id="pricing-service-group",
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="earliest",
            )
            await kafka_consumer.start()
            logger.info(f"Kafka Consumer connected & joined group successfully ({KAFKA_BOOTSTRAP_SERVERS}).")
            break  # Thoát khỏi vòng lặp kết nối nếu thành công
        except (GroupCoordinatorNotAvailableError, KafkaConnectionError) as e:
            logger.warning(f"Kafka Coordinator unavailable, retrying in 5 seconds... ({e})")
            if kafka_consumer:
                await kafka_consumer.stop()
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.error(f"Unexpected error initializing Kafka Consumer: {e}")
            await asyncio.sleep(5)

    # Đọc tin nhắn liên tục
    try:
        async for msg in kafka_consumer:
            try:
                data = msg.value
                event_name = data.get("event_name")
                user_id = str(data.get("user_id", "")).strip().lower()
                username = str(data.get("username", "")).strip()

                if user_id and username and event_name in ["USER_LOGGED_IN", "USER_SYNC"]:
                    db = SessionLocal()
                    try:
                        user_cache = (
                            db.query(UserCache)
                            .filter(UserCache.user_id == user_id)
                            .first()
                        )
                        if not user_cache:
                            user_cache = UserCache(
                                user_id=user_id,
                                username=username,
                                full_name=username,
                            )
                            db.add(user_cache)
                            logger.info(f"[Kafka Cache] Added new user: {username} ({user_id})")
                        else:
                            if user_cache.username != username:
                                user_cache.username = username
                                logger.info(f"[Kafka Cache] Updated user: {username} ({user_id})")
                        db.commit()
                    except Exception as db_err:
                        db.rollback()
                        logger.error(f"[Kafka Cache DB Error] {db_err}")
                    finally:
                        db.close()
            except Exception as msg_err:
                logger.error(f"Error processing Kafka message: {msg_err}")

    except asyncio.CancelledError:
        pass
    finally:
        if kafka_consumer:
            await kafka_consumer.stop()
            logger.info("Kafka Consumer (user-events) stopped.")


# 2. PAYMENT ISSUED CONSUMER (THÊM MỚI)
def save_payment_usage_log(data: dict):
    """Hàm synchronous ghi nhận lịch sử áp dụng bảng giá từ Payment Service."""
    db = SessionLocal()
    try:
        applied_at = (
            datetime.fromisoformat(data["occurredAt"].replace("Z", "+00:00"))
            if data.get("occurredAt")
            else datetime.utcnow()
        )

        # Idempotency Check (Tránh ghi trùng record)
        existing = (
            db.query(PriceListUsageLog)
            .filter(PriceListUsageLog.payment_board_id == data["id"])
            .first()
        )

        if not existing:
            usage_log = PriceListUsageLog(
                price_list_version_id=data["priceListVersionId"],
                payment_board_id=data["id"],
                payment_code=data.get("code"),
                status=data.get("status"),
                total_amount=data.get("totalAmount"),
                customer_id=data.get("customerId"),
                contract_id=data.get("contractId"),
                issued_by=data.get("issuedBy"),
                applied_at=applied_at,
            )
            db.add(usage_log)
            db.commit()
            logger.info(f"[Kafka Payment] Saved usage log for payment_board_id: {data['id']}")
    except Exception as db_err:
        db.rollback()
        logger.error(f"[Kafka Payment DB Error] {db_err}")
    finally:
        db.close()


async def consume_payment_events():
    global payment_consumer

    while True:
        try:
            payment_consumer = AIOKafkaConsumer(
                "payment.issued",
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                group_id="pricing-payment-issued",
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="earliest",
            )
            await payment_consumer.start()
            logger.info(f"Kafka Payment Consumer connected & listening on 'payment.issued' ({KAFKA_BOOTSTRAP_SERVERS}).")
            break
        except (GroupCoordinatorNotAvailableError, KafkaConnectionError) as e:
            logger.warning(f"Kafka Payment Coordinator unavailable, retrying in 5 seconds... ({e})")
            if payment_consumer:
                await payment_consumer.stop()
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.error(f"Unexpected error initializing Payment Consumer: {e}")
            await asyncio.sleep(5)

    try:
        async for msg in payment_consumer:
            try:
                data = msg.value
                if data.get("event") == "PAYMENT_ISSUED":
                    await asyncio.to_thread(save_payment_usage_log, data)
            except Exception as msg_err:
                logger.error(f"Error processing payment message: {msg_err}")
    except asyncio.CancelledError:
        pass
    finally:
        if payment_consumer:
            await payment_consumer.stop()
            logger.info("Kafka Payment Consumer stopped.")


# 3. START & STOP EVENTS (KHỞI CHẠY SONG SONG)
async def start_kafka_consumer():
    global consumer_task, payment_consumer_task
    consumer_task = asyncio.create_task(consume_user_events())
    payment_consumer_task = asyncio.create_task(consume_payment_events())


async def stop_kafka_consumer():
    global consumer_task, payment_consumer_task
    if consumer_task:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
            
    if payment_consumer_task:
        payment_consumer_task.cancel()
        try:
            await payment_consumer_task
        except asyncio.CancelledError:
            pass