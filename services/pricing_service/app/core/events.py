import asyncio
import json
import logging
import os
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import GroupCoordinatorNotAvailableError, KafkaConnectionError
from app.db.session import SessionLocal
from app.models.pricing import UserCache

logger = logging.getLogger("pricing_events")
kafka_consumer: AIOKafkaConsumer = None
consumer_task: asyncio.Task = None

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")


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
            logger.info("Kafka Consumer stopped.")


async def start_kafka_consumer():
    global consumer_task
    consumer_task = asyncio.create_task(consume_user_events())


async def stop_kafka_consumer():
    global consumer_task
    if consumer_task:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass