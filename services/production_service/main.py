from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from core.database import Base, engine
from api.operation import router as operation_router
from api.report import router as report_router
from core.kafka import kafka_producer
from consumers.cache_consumer import start_consumer
from tasks.outbox_relay import start_outbox_relay

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Production Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(operation_router, prefix="/api/v1", tags=["Operations"])
app.include_router(report_router, prefix="/api/v1/reports", tags=["Reports"])

@app.on_event("startup")
async def startup_event():
    await kafka_producer.start()
    asyncio.create_task(start_consumer())
    asyncio.create_task(start_outbox_relay(interval_seconds=60))

@app.on_event("shutdown")
async def shutdown_event():
    await kafka_producer.stop()

@app.get("/")
def read_root():
    return {"service": "Production Service", "status": "active"}