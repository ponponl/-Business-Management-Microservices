from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.operation import OperationPeriod, OperationVolume
from producers.event_producer import publish_period_locked
from datetime import datetime

class PeriodService:
    @staticmethod
    async def lock_period(db: Session, period_key: str, user_id: int):
        period = db.query(OperationPeriod).filter(OperationPeriod.period_key == period_key).first()
        if not period:
            raise HTTPException(status_code=404, detail="Period not found")
            
        if period.status == "LOCKED":
            raise HTTPException(status_code=400, detail="Period is already locked")
            
        period.status = "LOCKED"
        period.locked_at = datetime.utcnow()
        period.locked_by = user_id
        
        db.query(OperationVolume).filter(OperationVolume.period_key == period_key).update({"is_locked": True})
        
        db.commit()
        db.refresh(period)
        
        await publish_period_locked(period.period_key)
        return period
