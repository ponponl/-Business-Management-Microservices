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
ESIGN_MAX_RETRIES = max(1, int(os.getenv("ESIGN_MAX_RETRIES", "3")))
ESIGN_RETRY_BASE_SECONDS = max(0.1, float(os.getenv("ESIGN_RETRY_BASE_SECONDS", "2")))
ESIGN_REQUEST_TIMEOUT_SECONDS = max(1, float(os.getenv("ESIGN_REQUEST_TIMEOUT_SECONDS", "10")))


async def request_signature():
    """Replace the simulation with the external E-Sign request when available."""
    await asyncio.sleep(5)
    if random.random() >= 0.9:
        raise RuntimeError("E-Sign provider rejected or timed out the request")


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

        last_error = None
        for attempt in range(1, ESIGN_MAX_RETRIES + 1):
            try:
                await asyncio.wait_for(
                    request_signature(),
                    timeout=ESIGN_REQUEST_TIMEOUT_SECONDS,
                )
                last_error = None
                break
            except asyncio.CancelledError:
                raise
            except Exception as error:
                last_error = error
                if attempt < ESIGN_MAX_RETRIES:
                    delay = ESIGN_RETRY_BASE_SECONDS * (2 ** (attempt - 1))
                    logger.warning(
                        "E-Sign attempt %s/%s failed for %s; retrying in %.1fs: %s",
                        attempt,
                        ESIGN_MAX_RETRIES,
                        signature.id,
                        delay,
                        error,
                    )
                    await asyncio.sleep(delay)

        signature = db.execute(select(PaymentSignature).where(
            PaymentSignature.id == signature.id
        ).with_for_update()).scalar_one_or_none()
        if not signature or signature.status == "CANCELLED":
            return
        board = db.execute(select(PaymentBoard).where(
            PaymentBoard.id == payload["payment_board_id"]
        ).with_for_update()).scalar_one()
        success = last_error is None
        signature.status = "SIGNED" if success else "FAILED"
        signature.resolved_at = datetime.utcnow()
        board.status = "SIGNED" if success else "SIGN_FAILED"
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
        else:
            logger.error(
                "E-Sign failed after %s attempts for %s: %s",
                ESIGN_MAX_RETRIES,
                signature.id,
                last_error,
            )
        db.commit()
    except asyncio.CancelledError:
        db.rollback()
        raise
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