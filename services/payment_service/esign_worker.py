import asyncio
import json
import logging
import os
import random
from datetime import datetime

from aiokafka import AIOKafkaConsumer
from sqlalchemy import select

from models.database import SessionLocal, initialize_database
from models.payment import PaymentBoard, PaymentOutboxEvent, PaymentSignature

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("esign-worker")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")


async def process(message):
    payload = json.loads(message.value.decode("utf-8"))
    db = SessionLocal()
    try:
        signature = db.execute(select(PaymentSignature).where(
            PaymentSignature.id == payload["signature_id"]
        ).with_for_update()).scalar_one_or_none()
        if not signature or signature.status == "CANCELLED":
            return
        if signature.status != "PENDING":
            return
        board = db.execute(select(PaymentBoard).where(
            PaymentBoard.id == signature.payment_board_id
        ).with_for_update()).scalar_one()
        signature.status = "SIGNING"
        board.status = "SIGNING"
        db.commit()

        await asyncio.sleep(5)

        signature = db.execute(select(PaymentSignature).where(
            PaymentSignature.id == signature.id
        ).with_for_update()).scalar_one_or_none()
        if not signature or signature.status == "CANCELLED":
            return
        board = db.get(PaymentBoard, payload["payment_board_id"])
        success = random.random() < 0.9
        signature.status = "SIGNED" if success else "FAILED"
        signature.resolved_at = datetime.utcnow()
        board.status = "ISSUED" if success else "SIGN_FAILED"
        if success:
            db.add(PaymentOutboxEvent(
                event_type="payment.signing.succeeded",
                aggregate_id=board.id,
                payload=json.dumps({
                    "event": "PAYMENT_SIGNING_SUCCEEDED",
                    "payment_board_id": board.id,
                    "signature_id": signature.id,
                    "assignee_id": signature.assignee_id,
                    "occurred_at": datetime.utcnow().isoformat(),
                }),
            ))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to process signing event %s", payload.get("signature_id"))
        raise
    finally:
        db.close()


async def main():
    initialize_database()
    consumer = AIOKafkaConsumer(
        "payment.signing",
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="payment-esign-worker",
        auto_offset_reset="earliest",
    )
    await consumer.start()
    try:
        async for message in consumer:
            await process(message)
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(main())