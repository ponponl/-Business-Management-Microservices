from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.core.events import init_kafka, stop_kafka
from app.db.session import engine
from app.models.user import Base
from seed import seed_data

Base.metadata.create_all(bind=engine)
try:
    seed_data()
except Exception as e:
    print(f"Lỗi khi chạy seed data: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_kafka()
    yield
    await stop_kafka()

app = FastAPI(
    title="SV-01 Auth Service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

app.include_router(api_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8081, reload=True)