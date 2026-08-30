import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.messaging.kafka_producer import (
    kafka_producer,
)
from app.models.outbox_event import OutboxEvent


logger = logging.getLogger(__name__)


class OutboxPublisher:

    BATCH_SIZE = 100
    POLL_INTERVAL = 2
    MAX_RETRIES = 5

    @classmethod
    def get_pending_event_ids(
        cls,
        db: Session,
        limit: int,
    ) -> list:

        rows = (
            db.query(
                OutboxEvent.event_id
            )
            .filter(
                OutboxEvent.status == "PENDING"
            )
            .order_by(
                OutboxEvent.occurred_at.asc()
            )
            .limit(limit)
            .all()
        )

        return [
            event_id
            for (event_id,) in rows
        ]

    @classmethod
    async def publish_one(
        cls,
        event_id,
    ) -> bool:

        db = SessionLocal()

        try:

            event = (
                db.query(OutboxEvent)
                .filter(
                    OutboxEvent.event_id
                    == event_id,
                    OutboxEvent.status
                    == "PENDING",
                )
                .with_for_update()
                .first()
            )

            if event is None:
                return False

            try:

                logger.info(
                    "Publishing outbox event: "
                    "event_id=%s "
                    "event_type=%s "
                    "aggregate_id=%s",
                    event.event_id,
                    event.event_type,
                    event.aggregate_id,
                )

                await kafka_producer.publish(
                    topic=(
                        settings.KAFKA_CONTRACT_TOPIC
                    ),
                    key=str(
                        event.aggregate_id
                    ),
                    event=event.payload,
                )

                event.status = "PUBLISHED"

                event.published_at = (
                    datetime.now(timezone.utc)
                )

                event.last_error = None

                db.commit()

                logger.info(
                    "Outbox event marked PUBLISHED: "
                    "event_id=%s "
                    "event_type=%s",
                    event.event_id,
                    event.event_type,
                )

                return True

            except Exception as exc:

                db.rollback()

                failed_event = (
                    db.query(OutboxEvent)
                    .filter(
                        OutboxEvent.event_id
                        == event_id
                    )
                    .first()
                )

                if failed_event is not None:

                    failed_event.retry_count += 1

                    failed_event.last_error = (
                        str(exc)
                    )

                    if (
                        failed_event.retry_count
                        >= cls.MAX_RETRIES
                    ):
                        failed_event.status = (
                            "FAILED"
                        )

                    db.commit()

                    logger.warning(
                        "Outbox publish failed: "
                        "event_id=%s "
                        "retry_count=%s "
                        "status=%s "
                        "error=%s",
                        failed_event.event_id,
                        failed_event.retry_count,
                        failed_event.status,
                        failed_event.last_error,
                    )

                return False

        except Exception:

            db.rollback()

            logger.exception(
                "Unexpected error processing "
                "outbox event_id=%s",
                event_id,
            )

            return False

        finally:
            db.close()

    @classmethod
    async def publish_batch(cls) -> None:

        db = SessionLocal()

        try:

            event_ids = (
                cls.get_pending_event_ids(
                    db=db,
                    limit=cls.BATCH_SIZE,
                )
            )

        finally:
            db.close()

        if not event_ids:
            return

        for event_id in event_ids:

            await cls.publish_one(
                event_id
            )

    @classmethod
    async def run_forever(cls) -> None:

        logger.info(
            "Outbox Publisher started"
        )

        while True:

            try:

                await cls.publish_batch()

            except asyncio.CancelledError:

                logger.info(
                    "Outbox Publisher stopping"
                )

                raise

            except Exception:

                logger.exception(
                    "Unexpected Outbox Publisher error"
                )

            await asyncio.sleep(
                cls.POLL_INTERVAL
            )