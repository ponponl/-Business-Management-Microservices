from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.operation import OperationPeriod, UnlockPeriodRequest, OperationVolume, OperationOutboxEvent
from schemas.operation import UnlockRequestCreate, UnlockApprove
from producers.event_producer import publish_period_unlocked
import json
from datetime import datetime

class UnlockService:
    @staticmethod
    def create_request(db: Session, period_key: str, request_in: UnlockRequestCreate, user_id: int):
        period = db.query(OperationPeriod).filter(OperationPeriod.period_key == period_key).first()
        if not period or period.status != "LOCKED":
            raise HTTPException(status_code=400, detail="Period not locked or not found")
            
        req = UnlockPeriodRequest(
            period_key=period_key,
            requested_by=user_id,
            reason=request_in.reason,
            status="PENDING",
            target_type=request_in.target_type,
            target_volume_id=request_in.target_volume_id,
            target_service_code=request_in.target_service_code,
            old_quantity=request_in.old_quantity,
            proposed_quantity=request_in.proposed_quantity
        )
        db.add(req)
        db.commit()
        db.refresh(req)
        return req

    @staticmethod
    async def approve_request(db: Session, request_id: int, approve_in: UnlockApprove, user_id: int):
        req = db.query(UnlockPeriodRequest).filter(UnlockPeriodRequest.id == request_id).first()
        if not req:
            raise HTTPException(status_code=404, detail="Request not found")
            
        if req.status != "PENDING":
            raise HTTPException(status_code=400, detail="Request already processed")
            
        period = db.query(OperationPeriod).filter(OperationPeriod.period_key == req.period_key).first()
            
        req.approved_by = user_id
        req.approved_at = datetime.utcnow()
        
        if approve_in.approved:
            req.status = "APPROVED"
            outbox_event = None
            if req.target_type == "VOLUME" and req.target_volume_id:
                volume = db.query(OperationVolume).filter(OperationVolume.id == req.target_volume_id).first()
                if volume:
                    from models.operation import VolumeAuditLog
                    old_data = json.dumps({"quantity": volume.quantity}, default=str)
                    volume.quantity = req.proposed_quantity
                    new_data = json.dumps({"quantity": volume.quantity}, default=str)
                    
                    audit = VolumeAuditLog(
                        volume_id=volume.id,
                        action="UPDATE",
                        old_data=old_data,
                        new_data=new_data,
                        actor_id=str(user_id)
                    )
                    db.add(audit)
                    
                    event_payload = {
                        "volume_id": volume.id,
                        "period_key": volume.period_key
                    }
                    outbox_event = OperationOutboxEvent(
                        event_type="VOLUME_UPDATED",
                        payload=json.dumps(event_payload),
                        status="PENDING"
                    )
                    db.add(outbox_event)
            else:
                if period:
                    period.status = "OPEN"
                    period.locked_at = None
                    period.locked_by = None
                    db.query(OperationVolume).filter(OperationVolume.period_key == period.period_key).update({"is_locked": False})
                    
                    # Thêm Outbox Event vào chung Transaction
                    event_payload = {
                        "period_key": period.period_key
                    }
                    outbox_event = OperationOutboxEvent(
                        event_type="VOLUME_PERIOD_UNLOCKED",
                        payload=json.dumps(event_payload),
                        status="PENDING"
                    )
                    db.add(outbox_event)
                
            db.commit()
            
            if outbox_event:
                db.refresh(outbox_event)
                try:
                    if outbox_event.event_type == "VOLUME_PERIOD_UNLOCKED" and period:
                        await publish_period_unlocked(period.period_key)
                    outbox_event.status = "PUBLISHED"
                    db.commit()
                except Exception as e:
                    pass
        else:
            req.status = "REJECTED"
            req.reject_reason = approve_in.reject_reason
            db.commit()
            
        db.refresh(req)
        return req

    @staticmethod
    def get_requests(db: Session):
        return db.query(UnlockPeriodRequest).all()
