from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user  
from app.db.session import get_db
from app.schemas.approval import ApprovalActionRequest, ApprovalResponse
from app.services.approval_service import ApprovalService

router = APIRouter()


@router.get("/approval/stats")
def get_approval_stats(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """API lấy thống kê danh sách cho trang Quản lý (SUBMITTED, APPROVED, EFFECTIVE, REJECTED)"""
    return ApprovalService.get_approval_stats(db)


@router.get("/director-approval/stats")
def get_director_approval_stats(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """API lấy thống kê danh sách cho trang Giám đốc (APPROVED, EFFECTIVE, REJECTED)"""
    return ApprovalService.get_director_approval_stats(db)


@router.get("/director-list", response_model=List[ApprovalResponse])
def get_director_approval_list(
    status: Optional[str] = Query(None, description="Lọc theo trạng thái: APPROVED, EFFECTIVE, REJECTED"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """API lấy danh sách bảng giá cho trang Giám đốc (Chỉ gồm APPROVED, EFFECTIVE, REJECTED)"""
    return ApprovalService.get_director_approval_list(db=db, status=status)


# 2. API LẤY DANH SÁCH CHUNG
@router.get("", response_model=List[ApprovalResponse])
def get_approval_list(
    status: Optional[str] = Query(None, description="Lọc theo trạng thái: SUBMITTED, APPROVED, EFFECTIVE, REJECTED"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """API lấy danh sách bảng giá phục vụ trang Quản lý phê duyệt"""
    return ApprovalService.get_approval_list(db=db, status=status)


# 3. CÁC ROUTE XỬ LÝ THEO {price_code}
@router.post("/{price_code}/submit", response_model=ApprovalResponse)
def submit_price_list(
    price_code: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """API Nhân viên gửi duyệt bảng giá (Chuyển sang SUBMITTED)"""
    user_id = getattr(current_user, "id", None) or getattr(current_user, "user_id", None)
    return ApprovalService.submit_for_approval(db=db, price_code=price_code, user_id=user_id)


@router.post("/{price_code}/manager-approve", response_model=ApprovalResponse)
def manager_approve_price_list(
    price_code: str,
    payload: ApprovalActionRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """API Quản lý duyệt lần 1 (SUBMITTED -> APPROVED hoặc REJECTED)"""
    user_id = getattr(current_user, "id", None) or getattr(current_user, "user_id", None)
    return ApprovalService.manager_approve(db=db, price_code=price_code, payload=payload, manager_id=user_id)


@router.post("/{price_code}/director-approve", response_model=ApprovalResponse)
def director_approve_price_list(
    price_code: str,
    payload: ApprovalActionRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """API Giám đốc duyệt lần 2 (APPROVED -> EFFECTIVE hoặc REJECTED)"""
    user_id = getattr(current_user, "id", None) or getattr(current_user, "user_id", None)
    return ApprovalService.director_approve(db=db, price_code=price_code, payload=payload, director_id=user_id)