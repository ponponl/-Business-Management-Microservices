from fastapi import FastAPI
from app.db.session import engine, Base
import app.models.pricing  

# Tự động tạo toàn bộ các Bảng trong PostgreSQL nếu chưa tồn tại
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Pricing Service")

@app.get("/")
def read_root():
    return {
        "service": "Pricing Service",
        "status": "active",
        "database": "Connected & Tables Synced"
    }