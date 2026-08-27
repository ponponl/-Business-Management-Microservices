# app/api/v1/api.py
from fastapi import APIRouter
from app.api.v1.endpoints import price_list, approval, payment_integration, price_history

api_router = APIRouter()

# 1. Router Quản lý Bảng giá
api_router.include_router(
    price_list.router, 
    prefix="/price-lists", 
    tags=["Price Lists"]
)

# 2. Router Phê duyệt 
api_router.include_router(
    approval.router, 
    prefix="/approvals", 
    tags=["Approvals"]
)

# 3. Router xác thực cho Payment Service
api_router.include_router(
    payment_integration.router,
    prefix="/payment-integration",
    tags=["Payment Integration"]
)

# 4. Router Xem lịch sử phiên bản & Chi tiết
api_router.include_router(
    price_history.router,
    prefix="/price-history",
    tags=["Price History & Version Details"]
)