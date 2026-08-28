from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from models.operation import OperationVolume, OperationPeriod, VolumeAuditLog
from models.cache import ContractCache
from schemas.operation import VolumeCreate, VolumeUpdate
from producers.event_producer import publish_volume_recorded
import json
from datetime import datetime

class OperationService:
    @staticmethod
    async def create_volume(db: Session, volume_in: VolumeCreate, user_id: int):
        if volume_in.quantity <= 0:
            raise HTTPException(status_code=400, detail="Quantity must be > 0")

        contract = db.query(ContractCache).filter(ContractCache.id == volume_in.contract_id).first()
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found in cache")
            
        vol_date = volume_in.volume_date.replace(tzinfo=None)
        start_date = contract.start_date.replace(tzinfo=None)
        end_date = contract.end_date.replace(tzinfo=None)
        
        if not (start_date <= vol_date <= end_date):
            raise HTTPException(status_code=400, detail="Volume date is outside contract validity period")

        period = db.query(OperationPeriod).filter(OperationPeriod.period_key == volume_in.period_key).first()
        if period and period.status == "LOCKED":
            raise HTTPException(status_code=400, detail="Period is locked")
            
        if not period:
            period = OperationPeriod(period_key=volume_in.period_key, status="OPEN")
            db.add(period)
            db.commit()
            db.refresh(period)

        new_volume = OperationVolume(
            **volume_in.model_dump(),
            recorded_by=user_id
        )
        db.add(new_volume)
        db.commit()
        db.refresh(new_volume)

        audit = VolumeAuditLog(
            volume_id=new_volume.id,
            action="CREATE",
            new_data=json.dumps(volume_in.model_dump(), default=str),
            actor_id=user_id
        )
        db.add(audit)
        db.commit()
        
        await publish_volume_recorded(new_volume.id, new_volume.period_key)
        return new_volume
        
    @staticmethod
    async def update_volume(db: Session, volume_id: int, volume_in: VolumeUpdate, user_id: int):
        volume = db.query(OperationVolume).filter(OperationVolume.id == volume_id).first()
        if not volume:
            raise HTTPException(status_code=404, detail="Volume not found")
            
        period = db.query(OperationPeriod).filter(OperationPeriod.period_key == volume.period_key).first()
        if period and period.status == "LOCKED":
            raise HTTPException(status_code=400, detail="Period is locked")
            
        if volume_in.quantity <= 0:
            raise HTTPException(status_code=400, detail="Quantity must be > 0")
            
        old_data = {
            "quantity": volume.quantity,
            "unit": volume.unit
        }
        
        volume.quantity = volume_in.quantity
        if volume_in.unit:
            volume.unit = volume_in.unit
            
        db.commit()
        db.refresh(volume)
        
        new_data = {
            "quantity": volume.quantity,
            "unit": volume.unit
        }
        
        audit = VolumeAuditLog(
            volume_id=volume.id,
            action="UPDATE",
            old_data=json.dumps(old_data, default=str),
            new_data=json.dumps(new_data, default=str),
            actor_id=user_id
        )
        db.add(audit)
        db.commit()
        
        await publish_volume_recorded(volume.id, volume.period_key)
        return volume

    @staticmethod
    def get_volumes(db: Session, customer_id: int = None, contract_id: int = None, period_key: str = None):
        query = db.query(OperationVolume)
        if customer_id:
            query = query.filter(OperationVolume.customer_id == customer_id)
        if contract_id:
            query = query.filter(OperationVolume.contract_id == contract_id)
        if period_key:
            query = query.filter(OperationVolume.period_key == period_key)
        return query.all()

    # Lấy dữ liệu cho Payment Service
    @staticmethod
    def get_billing_volumes(
        db: Session, 
        customer_id: int = None, 
        contract_id: int = None, 
        period_start: str = None, 
        period_end: str = None, 
        service_code: str = None
    ):
        query = db.query(
            OperationVolume.id,
            OperationVolume.customer_id,
            OperationVolume.contract_id,
            OperationVolume.service_code,
            OperationVolume.volume_date,
            OperationVolume.period_key,
            OperationVolume.quantity,
            OperationVolume.unit,
            OperationVolume.is_locked,
            OperationPeriod.status.label("period_status")
        ).join(
            OperationPeriod, OperationVolume.period_key == OperationPeriod.period_key
        )

        if customer_id:
            query = query.filter(OperationVolume.customer_id == customer_id)
        if contract_id:
            query = query.filter(OperationVolume.contract_id == contract_id)
        if service_code:
            query = query.filter(OperationVolume.service_code == service_code)
        if period_start:
            query = query.filter(OperationVolume.period_key >= period_start)
        if period_end:
            query = query.filter(OperationVolume.period_key <= period_end)
            
        return query.all()

    @staticmethod
    def get_audit_logs(db: Session, volume_id: int):
        return db.query(VolumeAuditLog).filter(VolumeAuditLog.volume_id == volume_id).all()
