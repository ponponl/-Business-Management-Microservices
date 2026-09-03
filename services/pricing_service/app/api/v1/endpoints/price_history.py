from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.price_history import (
    VersionHistoryItem,
    VersionDetailResponse,
    ChangeHistoryItem,
    UsageLogItem,
    VersionComparisonResponse,
)
from app.services.price_history_service import PriceHistoryService

router = APIRouter()


@router.get(
    "/price-lists/{price_list_identifier}/versions",
    response_model=List[VersionHistoryItem],
    status_code=status.HTTP_200_OK,
    summary="Lấy danh sách lịch sử các phiên bản (Sidebar)"
)
def get_version_history_list(price_list_identifier: str, db: Session = Depends(get_db)):
    """Lấy danh sách phiên bản thuộc bảng giá (chấp nhận cả UUID lẫn Mã bảng giá dạng chuỗi)."""
    return PriceHistoryService.get_version_history_list(db, price_list_identifier)


@router.get(
    "/versions/compare",
    response_model=VersionComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="So sánh chênh lệch đơn giá giữa 2 phiên bản"
)
def compare_versions(
    source_version_id: UUID = Query(..., description="ID phiên bản gốc/cũ (VD: v3.0)"),
    target_version_id: UUID = Query(..., description="ID phiên bản so sánh/mới (VD: v3.1)"),
    db: Session = Depends(get_db)
):
    """
    So sánh giá dịch vụ giữa 2 phiên bản:
    - **source_version_id**: Phiên bản làm mốc (VD: v3.0 - EFFECTIVE)
    - **target_version_id**: Phiên bản đối chiếu (VD: v3.1 - DRAFT)
    
    Trả về danh sách các dịch vụ kèm chênh lệch số tiền (+/- VND), % chênh lệch và trạng thái thay đổi.
    """
    return PriceHistoryService.compare_versions(
        db=db,
        source_version_id=source_version_id,
        target_version_id=target_version_id
    )


@router.get(
    "/versions/{version_id}/details",
    response_model=VersionDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy chi tiết cấu hình đơn giá của phiên bản (Tab 1)"
)
def get_version_details(version_id: UUID, db: Session = Depends(get_db)):
    """Tab 1: Lấy thông tin chi tiết bảng giá và các đơn giá dịch vụ."""
    return PriceHistoryService.get_version_details(db, version_id)


@router.get(
    "/versions/{version_id}/change-logs",
    response_model=List[ChangeHistoryItem],
    status_code=status.HTTP_200_OK,
    summary="Lấy nhật ký thay đổi của phiên bản (Tab 2)"
)
def get_change_logs(version_id: UUID, db: Session = Depends(get_db)):
    """Tab 2: Lấy thông tin lịch sử chỉnh sửa các trường dữ liệu."""
    return PriceHistoryService.get_change_logs(db, version_id)


@router.get(
    "/versions/{version_id}/usage-logs",
    response_model=List[UsageLogItem],
    status_code=status.HTTP_200_OK,
    summary="Lấy lịch sử áp dụng bảng giá (Tab 3)"
)
def get_usage_logs(version_id: UUID, db: Session = Depends(get_db)):
    """Tab 3: Lấy danh sách lượt áp dụng phiên bản bảng giá từ Payment Board."""
    return PriceHistoryService.get_usage_logs(db, version_id)