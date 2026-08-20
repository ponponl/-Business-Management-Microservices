from fastapi import APIRouter, Depends, Query,  HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.schemas.price_list import PriceListStatsResponse, PriceListPaginatedResponse, PriceListCreate
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


@router.get("/{price_code}")
def get_price_list_detail(price_code: str, db: Session = Depends(get_db)):
    """Lấy thông tin chi tiết của 1 bảng giá"""
    return PriceListService.get_detail_by_code(db=db, price_code=price_code)



@router.post("", status_code=status.HTTP_201_CREATED)
def create_new_price_list(
    payload: PriceListCreate, 
    db: Session = Depends(get_db)
):
    try:
        new_price_list = PriceListService.create_price_list(db, payload)
        return {
            "message": "Tạo bảng giá thành công",
            "data": new_price_list
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400, 
            detail=f"Không thể tạo bảng giá: {str(e)}"
        )