from fastapi import APIRouter
from app.api.v1.endpoints import price_list

api_router = APIRouter()
api_router.include_router(price_list.router, prefix="/price-lists", tags=["Price Lists"])