from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.operation import OperationVolume, OperationPeriod, VolumeAuditLog, OperationOutboxEvent
from models.cache import ContractCache
from schemas.operation import VolumeCreate, VolumeUpdate
from producers.event_producer import publish_volume_recorded
import json

class OperationService:
    @staticmethod
    async def create_volume(db: Session, volume_in: VolumeCreate, user_id: int):
        if volume_in.quantity <= 0:
            raise HTTPException(status_code=400, detail="Quantity must be > 0")

        from sqlalchemy import or_
        # Tìm contract trong danh bạ cache bằng contract_id (UUID) hoặc contract_number
        contract = db.query(ContractCache).filter(
            or_(
                ContractCache.contract_id == volume_in.contract_id,
                ContractCache.contract_number == volume_in.contract_id
            )
        ).first()
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found in cache")
            
        if contract.status not in ["APPROVED", "ACTIVE"]:
            raise HTTPException(status_code=400, detail="Contract is not approved or active")
            
        vol_date = volume_in.volume_date.replace(tzinfo=None)
        if contract.start_date and contract.end_date:
            start_date = contract.start_date.replace(tzinfo=None)
            end_date = contract.end_date.replace(tzinfo=None)
            
            if not (start_date <= vol_date <= end_date):
                raise HTTPException(status_code=400, detail="Volume date is outside contract validity period")

        period = db.query(OperationPeriod).filter(OperationPeriod.period_key == volume_in.period_key).first()
        if period and period.status == "LOCKED":
            from models.operation import UnlockPeriodRequest
            approved_req = db.query(UnlockPeriodRequest).filter(
                UnlockPeriodRequest.period_key == volume_in.period_key,
                UnlockPeriodRequest.requested_by == str(user_id),
                UnlockPeriodRequest.status == "APPROVED",
                UnlockPeriodRequest.target_type == "PERIOD"
            ).first()
            if not approved_req:
                raise HTTPException(status_code=400, detail="Period is locked")
            
        if not period:
            period = OperationPeriod(period_key=volume_in.period_key, status="OPEN")
            db.add(period)

        new_volume = OperationVolume(
            **volume_in.model_dump(),
            recorded_by=user_id
        )
        db.add(new_volume)
        db.flush()  # Dùng flush để lấy new_volume.id mà không cần commit sớm

        audit = VolumeAuditLog(
            volume_id=new_volume.id,
            action="CREATE",
            new_data=json.dumps(volume_in.model_dump(), default=str),
            actor_id=user_id
        )
        db.add(audit)
        
        # Thêm Outbox Event vào chung Transaction
        event_payload = {
            "volume_id": new_volume.id,
            "period_key": new_volume.period_key
        }
        outbox_event = OperationOutboxEvent(
            event_type="VOLUME_RECORDED",
            payload=json.dumps(event_payload),
            status="PENDING"
        )
        db.add(outbox_event)
        
        db.commit()
        db.refresh(outbox_event)
        
        try:
            await publish_volume_recorded(new_volume.id, new_volume.period_key)
            outbox_event.status = "PUBLISHED"
            db.commit()
        except Exception as e:
            # Nếu Kafka lỗi, outbox_event vẫn lưu trạng thái PENDING để có thể retry sau
            pass
            
        return new_volume
        
    @staticmethod
    async def update_volume(db: Session, volume_id: int, volume_in: VolumeUpdate, user_id: int):
        volume = db.query(OperationVolume).filter(OperationVolume.id == volume_id).first()
        if not volume:
            raise HTTPException(status_code=404, detail="Volume not found")
            
        period = db.query(OperationPeriod).filter(OperationPeriod.period_key == volume.period_key).first()
        if period and period.status == "LOCKED":
            from models.operation import UnlockPeriodRequest
            from sqlalchemy import or_, and_
            approved_req = db.query(UnlockPeriodRequest).filter(
                UnlockPeriodRequest.period_key == volume.period_key,
                UnlockPeriodRequest.requested_by == str(user_id),
                UnlockPeriodRequest.status == "APPROVED",
                or_(
                    UnlockPeriodRequest.target_type == "PERIOD",
                    and_(
                        UnlockPeriodRequest.target_type == "VOLUME",
                        UnlockPeriodRequest.target_volume_id == volume.id
                    )
                )
            ).first()
            if not approved_req:
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
            
        db.flush()  # Dùng flush để đánh dấu thay đổi thay vì commit sớm
        
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
        
        # Thêm Outbox Event vào chung Transaction
        event_payload = {
            "volume_id": volume.id,
            "period_key": volume.period_key
        }
        outbox_event = OperationOutboxEvent(
            event_type="VOLUME_RECORDED",
            payload=json.dumps(event_payload),
            status="PENDING"
        )
        db.add(outbox_event)
        
        db.commit()
        db.refresh(outbox_event)
        
        try:
            await publish_volume_recorded(volume.id, volume.period_key)
            outbox_event.status = "PUBLISHED"
            db.commit()
        except Exception as e:
            pass
            
        return volume

    @staticmethod
    def get_volumes(db: Session, contract_id: str = None, period_key: str = None):
        query = db.query(OperationVolume, ContractCache.contract_number).outerjoin(
            ContractCache, OperationVolume.contract_id == ContractCache.contract_id
        )
        if contract_id:
            query = query.filter(OperationVolume.contract_id == contract_id)
        if period_key:
            query = query.filter(OperationVolume.period_key == period_key)
            
        results = query.order_by(
            OperationVolume.is_locked.asc(),
            OperationVolume.volume_date.desc()
        ).all()
        
        formatted_results = []
        for vol, contract_number in results:
            formatted_results.append({
                "id": vol.id,
                "contract_id": vol.contract_id,
                "contract_number": contract_number,
                "service_code": vol.service_code,
                "volume_date": vol.volume_date,
                "period_key": vol.period_key,
                "quantity": vol.quantity,
                "unit": vol.unit,
                "recorded_by": str(vol.recorded_by),
                "is_locked": vol.is_locked,
                "created_at": vol.created_at,
                "updated_at": vol.updated_at
            })
            
        return formatted_results

    # Lấy dữ liệu cho Payment Service
    @staticmethod
    def get_billing_volumes(
        db: Session, 
        contract_id: str = None, 
        period_start: str = None, 
        period_end: str = None, 
        service_code: str = None
    ):
        query = db.query(
            OperationVolume.id,
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

    @staticmethod
    def get_active_contracts(db: Session):
        return db.query(ContractCache).filter(ContractCache.status.in_(["ACTIVE", "APPROVED"])).all()
