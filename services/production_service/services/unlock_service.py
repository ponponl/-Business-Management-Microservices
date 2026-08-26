from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.operation import OperationPeriod, UnlockPeriodRequest, OperationVolume
from schemas.operation import UnlockRequestCreate, UnlockApprove
from producers.event_producer import publish_period_unlocked
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
            status="PENDING"
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
            if period:
                period.status = "OPEN"
                period.locked_at = None
                period.locked_by = None
                db.query(OperationVolume).filter(OperationVolume.period_key == period.period_key).update({"is_locked": False})
            db.commit()
            if period:
                await publish_period_unlocked(period.period_key)
        else:
            req.status = "REJECTED"
            req.reject_reason = approve_in.reject_reason
            db.commit()
            
        db.refresh(req)
        return req
