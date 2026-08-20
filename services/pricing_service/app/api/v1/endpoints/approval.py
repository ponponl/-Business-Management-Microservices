from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session
from typing import Optional, List

from app.db.session import get_db
from app.schemas.approval import ApprovalActionRequest, ApprovalResponse
from app.services.approval_service import ApprovalService

router = APIRouter()


# 1. BẮT BUỘC ĐẶT ROUTE TĨNH NÀY LÊN ĐẦU TIÊN để không bị đè bởi {price_code}
@router.get("/approval/stats")
def get_approval_stats(db: Session = Depends(get_db)):
    return ApprovalService.get_approval_stats(db)


# 2. API Lấy danh sách bảng giá
@router.get("", response_model=List[ApprovalResponse])
def get_approval_list(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """API lấy danh sách toàn bộ bảng giá phục vụ trang Quản lý phê duyệt"""
    return ApprovalService.get_approval_list(db=db, status=status)


# 3. API Nhân viên gửi duyệt
@router.post("/{price_code}/submit", response_model=ApprovalResponse)
def submit_price_list(
    price_code: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db)
):
    """API Nhân viên gửi duyệt bảng giá"""
    return ApprovalService.submit_for_approval(db=db, price_code=price_code, user_id=x_user_id)


# 4. API Quản lý phê duyệt / Từ chối
@router.post("/{price_code}/manager-approve", response_model=ApprovalResponse)
def manager_approve_price_list(
    price_code: str,
    payload: ApprovalActionRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db)
):
    """API Quản lý duyệt lần 1 (APPROVE hoặc REJECT)"""
    return ApprovalService.manager_approve(db=db, price_code=price_code, payload=payload, manager_id=x_user_id)