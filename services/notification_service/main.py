from fastapi import FastAPI
from contextlib import asynccontextmanager
from core.database import engine, Base
from core.config import settings
from api.v1.router import api_router
from consumers.notification_consumer import start_consumer, stop_consumer
import asyncio

Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi động Kafka Consumer trong background
    consumer_task = asyncio.create_task(start_consumer())
    yield
    # Dừng Kafka Consumer khi shutdown
    await stop_consumer()
    consumer_task.cancel()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {"message": "Welcome to Notification Service"}
