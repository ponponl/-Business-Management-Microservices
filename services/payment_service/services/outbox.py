import asyncio
import json
import logging
import os
from datetime import datetime

from aiokafka import AIOKafkaProducer
from sqlalchemy import select

from models.database import SessionLocal
from models.payment import PaymentOutboxEvent

logger = logging.getLogger("payment-service")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")


class OutboxPublisher:
    def __init__(self):
        self.producer = None

    async def run(self):
        while True:
            db = SessionLocal()
            try:
                if self.producer is None:
                    self.producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
                    await self.producer.start()
                events = db.scalars(select(PaymentOutboxEvent).where(
                    PaymentOutboxEvent.published_at.is_(None)
                ).order_by(PaymentOutboxEvent.created_at).limit(20)).all()
                for event in events:
                    await self.producer.send_and_wait(event.event_type, event.payload.encode("utf-8"))
                    event.published_at = datetime.utcnow()
                db.commit()
            except Exception:
                db.rollback()
                logger.exception("Outbox publish failed; retrying pending events")
                if self.producer:
                    try:
                        await self.producer.stop()
                    except Exception:
                        logger.exception("Kafka producer shutdown failed")
                    self.producer = None
            finally:
                db.close()
            await asyncio.sleep(2)

    async def stop(self):
        if self.producer:
            await self.producer.stop()
            self.producer = None
