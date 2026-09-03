import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1.payments import router as v1_payments_router
from models.database import initialize_database
from services.outbox import OutboxPublisher


initialize_database()
outbox_publisher = OutboxPublisher()


async def lifespan(app: FastAPI):
    task = asyncio.create_task(outbox_publisher.run())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await outbox_publisher.stop()


app = FastAPI(title="Payment Service API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"service": "Payment Service", "status": "active", "database": "Connected & Tables Synced"}


app.include_router(v1_payments_router)
