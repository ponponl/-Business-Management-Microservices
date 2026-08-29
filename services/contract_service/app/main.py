import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.scheduler import (
    start_scheduler,
    stop_scheduler,
)
from app.messaging.kafka_producer import (
    kafka_producer,
)
from app.services.outbox_publisher import (
    OutboxPublisher,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # =====================================================
    # STARTUP
    # =====================================================
    # 1. Start Kafka Producer
    await kafka_producer.start()

    # 2. Start Outbox Publisher
    outbox_task = asyncio.create_task(
        OutboxPublisher.run_forever()
    )

    # 3. Start Contract Lifecycle Scheduler
    start_scheduler()

    logger.info("Contract Service startup completed")

    try:
        yield
    finally:
        # =================================================
        # SHUTDOWN
        # =================================================
        # 1. Stop Lifecycle Scheduler
        stop_scheduler()

        # 2. Stop Outbox Publisher
        outbox_task.cancel()
        try:
            await outbox_task
        except asyncio.CancelledError:
            pass

        # 3. Stop Kafka Producer
        await kafka_producer.stop()

        logger.info("Contract Service shutdown completed")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.include_router(
    api_router,
    prefix="/api/v1",
)


@app.get("/")
def root():
    return {
        "service": "contract-service",
        "status": "running",
    }