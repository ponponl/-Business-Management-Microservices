import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.session import engine, Base
import app.models.pricing 
from app.api.v1.api import api_router
from app.core.events import start_kafka_consumer, stop_kafka_consumer

@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: Base.metadata.create_all(bind=engine))
    
    await start_kafka_consumer()
    
    yield
    
    await stop_kafka_consumer()

app = FastAPI(
    title="Pricing Service API",
    description="API hệ thống quản lý đơn giá và phê duyệt giá dịch vụ logistics",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://127.0.0.1:5173",
        "http://localhost:3000"   
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {
        "service": "Pricing Service",
        "status": "active",
        "database": "Connected & Tables Synced"
    }