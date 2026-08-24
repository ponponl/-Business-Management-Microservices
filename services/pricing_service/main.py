from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.session import engine, Base
import app.models.pricing 
from app.api.v1.api import api_router
from app.core.events import start_kafka_consumer, stop_kafka_consumer

# 1. Tự động tạo toàn bộ các Bảng trong PostgreSQL nếu chưa tồn tại
Base.metadata.create_all(bind=engine)

# 2. Quản lý vòng đời ứng dụng 
@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_kafka_consumer()
    yield
    await stop_kafka_consumer()

# 3. Khởi tạo ứng dụng FastAPI
app = FastAPI(
    title="Pricing Service API",
    description="API hệ thống quản lý đơn giá và phê duyệt giá dịch vụ logistics",
    version="1.0.0",
    lifespan=lifespan
)

# 4. Cấu hình Middleware CORS 
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://127.0.0.1:5173",
        "http://localhost:3000"   
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 5. Tích hợp Router API v1
app.include_router(api_router, prefix="/api/v1")

# 6. Endpoint kiểm tra trạng thái Service (Health Check)
@app.get("/")
def read_root():
    return {
        "service": "Pricing Service",
        "status": "active",
        "database": "Connected & Tables Synced"
    }