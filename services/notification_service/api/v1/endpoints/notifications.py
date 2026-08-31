from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from core.database import get_db
from schemas.notification import NotificationResponse
from services.notification_service import NotificationService

router = APIRouter()

# TODO: Thêm Dependency lấy user_id từ JWT Token sau khi ghép chung hệ thống auth
# Tạm thời hardcode hoặc truyền qua header/query để test

@router.get("/", response_model=List[NotificationResponse])
def get_notifications(
    user_id: int, 
    skip: int = 0, 
    limit: int = 50, 
    unread_only: bool = False,
    db: Session = Depends(get_db)
):
    return NotificationService.get_user_notifications(db, user_id, skip, limit, unread_only)

@router.put("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_as_read(
    notification_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    return NotificationService.mark_as_read(db, notification_id, user_id)

@router.put("/read-all")
def mark_all_notifications_as_read(
    user_id: int,
    db: Session = Depends(get_db)
):
    return NotificationService.mark_all_as_read(db, user_id)
