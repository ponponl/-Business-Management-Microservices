from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.schemas.price_list import PriceListStatsResponse, PriceListPaginatedResponse
from app.services.price_list_service import PriceListService

router = APIRouter()


@router.get("/stats", response_model=PriceListStatsResponse)
def get_price_list_stats(db: Session = Depends(get_db)):
    """Lấy số lượng thống kê cho 4 thẻ Stat Cards"""
    return PriceListService.get_stats(db)


@router.get("", response_model=PriceListPaginatedResponse)
def get_price_lists(
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    customer: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Lấy danh sách bảng giá phân trang, hỗ trợ đầy đủ bộ lọc và tìm kiếm"""
    return PriceListService.get_paginated_list(
        db=db,
        status=status,
        apply_type=type,
        customer=customer,
        search=search,
        page=page,
        page_size=page_size
    )