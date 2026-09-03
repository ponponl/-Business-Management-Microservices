from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.notification import Notification
from schemas.notification import NotificationCreate

class NotificationService:
    @staticmethod
    def create_notification(db: Session, notif_in: NotificationCreate):
        notif = Notification(**notif_in.model_dump())
        db.add(notif)
        db.commit()
        db.refresh(notif)
        return notif

    @staticmethod
    def get_user_notifications(db: Session, user_id: int, skip: int = 0, limit: int = 50, unread_only: bool = False):
        query = db.query(Notification).filter(Notification.user_id == user_id)
        if unread_only:
            query = query.filter(Notification.is_read == False)
        return query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def mark_as_read(db: Session, notification_id: int, user_id: int):
        notif = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == user_id).first()
        if not notif:
            raise HTTPException(status_code=404, detail="Notification not found")
        notif.is_read = True
        db.commit()
        db.refresh(notif)
        return notif

    @staticmethod
    def mark_all_as_read(db: Session, user_id: int):
        db.query(Notification).filter(Notification.user_id == user_id, Notification.is_read == False).update({"is_read": True})
        db.commit()
        return {"message": "All notifications marked as read"}
