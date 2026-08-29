import json
import logging

from aiokafka import AIOKafkaProducer

from app.core.config import settings


logger = logging.getLogger(__name__)


class KafkaProducer:

    def __init__(self) -> None:
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:

        if self._producer is not None:
            return

        self._producer = AIOKafkaProducer(
            bootstrap_servers=(
                settings.KAFKA_BOOTSTRAP_SERVERS
            ),
        )

        await self._producer.start()

        logger.info(
            "Kafka Producer started: %s",
            settings.KAFKA_BOOTSTRAP_SERVERS,
        )

    async def stop(self) -> None:

        if self._producer is None:
            return

        try:
            await self._producer.stop()

        finally:
            self._producer = None

        logger.info(
            "Kafka Producer stopped"
        )

    async def publish(
        self,
        *,
        topic: str,
        key: str,
        event: dict,
    ):

        if self._producer is None:
            raise RuntimeError(
                "Kafka Producer has not been started"
            )

        value = json.dumps(
            event,
            ensure_ascii=False,
        ).encode("utf-8")

        key_bytes = key.encode("utf-8")

        metadata = await self._producer.send_and_wait(
            topic,
            key=key_bytes,
            value=value,
        )

        logger.info(
            "Kafka event published: "
            "event_id=%s "
            "event_type=%s "
            "topic=%s "
            "partition=%s "
            "offset=%s "
            "key=%s",
            event.get("event_id"),
            event.get("event_name"),
            topic,
            metadata.partition,
            metadata.offset,
            key,
        )

        return metadata


kafka_producer = KafkaProducer()