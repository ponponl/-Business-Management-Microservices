from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user, require_roles
from app.db.session import get_db
from app.schemas.price_list import (
    PriceListCreate,
    PriceListPaginatedResponse,
    PriceListStatsResponse,
    ServiceItemResponse,  
)
from app.services.price_list_service import PriceListService
from app.models.pricing import ServiceItem

router = APIRouter()


@router.get("/stats", response_model=PriceListStatsResponse)
def get_price_list_stats(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Lấy số lượng thống kê cho 5 thẻ Stat Cards"""
    return PriceListService.get_stats(db)


@router.get("", response_model=PriceListPaginatedResponse)
def get_price_lists(
    status_filter: Optional[str] = Query(None, alias="status"),
    type: Optional[str] = Query(None),
    customer: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Lấy danh sách bảng giá phân trang, hỗ trợ đầy đủ bộ lọc và tìm kiếm"""
    return PriceListService.get_paginated_list(
        db=db,
        status_filter=status_filter,
        apply_type=type,
        customer=customer,
        search=search,
        page=page,
        page_size=page_size,
    )


# --- ROUTE NÀY NẰM TRƯỚC ROUTE /{price_code} LÀ CHÍNH XÁC ---
@router.get("/services", response_model=List[ServiceItemResponse])  # <-- Gắn response_model
def get_services_from_db(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Lấy danh sách các dịch vụ (ServiceItem) đang ACTIVE từ PostgreSQL"""
    try:
        # Lấy danh sách dịch vụ có trạng thái ACTIVE
        services = db.query(ServiceItem).filter(ServiceItem.status == "ACTIVE").all()
        return services
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy danh sách dịch vụ: {str(e)}",
        )


@router.get("/{price_code}")
def get_price_list_detail(
    price_code: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Lấy thông tin chi tiết của 1 bảng giá"""
    return PriceListService.get_detail_by_code(db=db, price_code=price_code)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_new_price_list(
    payload: PriceListCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles(["STAFF", "MANAGER", "ADMIN"])),
):
    """Tạo mới một bảng giá"""
    try:
        new_price_list = PriceListService.create_price_list(
            db=db, payload=payload, current_user=current_user
        )
        return {"message": "Tạo bảng giá thành công", "data": new_price_list}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Không thể tạo bảng giá: {str(e)}",
        )


@router.put("/{price_code}")
def update_price_list(
    price_code: str,
    payload: PriceListCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles(["STAFF", "MANAGER", "ADMIN"])),
):
    """API Cập nhật Bảng giá (Chỉ DRAFT và REJECTED mới được sửa)"""
    return PriceListService.update_price_list(
        db=db,
        price_code=price_code,
        payload=payload,
        current_user=current_user,
    )