from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import require_role
from schemas.operation import VolumeCreate, VolumeUpdate, VolumeResponse, UnlockRequestCreate, UnlockApprove, UnlockRequestResponse
from services.operation_service import OperationService
from services.period_service import PeriodService
from services.unlock_service import UnlockService

router = APIRouter()

@router.post("/volumes", response_model=VolumeResponse)
async def create_volume(volume_in: VolumeCreate, db: Session = Depends(get_db), user: dict = Depends(require_role(["OPERATION_STAFF", "OPERATION_MANAGER"]))):
    return await OperationService.create_volume(db, volume_in, user["sub"])

@router.put("/volumes/{volume_id}", response_model=VolumeResponse)
async def update_volume(volume_id: int, volume_in: VolumeUpdate, db: Session = Depends(get_db), user: dict = Depends(require_role(["OPERATION_STAFF", "OPERATION_MANAGER"]))):
    return await OperationService.update_volume(db, volume_id, volume_in, user["sub"])

@router.get("/volumes")
def get_volumes(customer_id: int = None, contract_id: int = None, period_key: str = None, db: Session = Depends(get_db), user: dict = Depends(require_role(["OPERATION_STAFF", "OPERATION_MANAGER", "DIRECTOR"]))):
    return OperationService.get_volumes(db, customer_id, contract_id, period_key)

@router.get("/volumes/{volume_id}/audit-logs")
def get_audit_logs(volume_id: int, db: Session = Depends(get_db), user: dict = Depends(require_role(["OPERATION_STAFF", "OPERATION_MANAGER", "DIRECTOR"]))):
    return OperationService.get_audit_logs(db, volume_id)

@router.post("/periods/{period_key}/lock")
async def lock_period(period_key: str, db: Session = Depends(get_db), user: dict = Depends(require_role(["OPERATION_MANAGER"]))):
    return await PeriodService.lock_period(db, period_key, user["sub"])

@router.post("/periods/{period_key}/unlock-request", response_model=UnlockRequestResponse)
def request_unlock(period_key: str, request_in: UnlockRequestCreate, db: Session = Depends(get_db), user: dict = Depends(require_role(["OPERATION_MANAGER"]))):
    return UnlockService.create_request(db, period_key, request_in, user["sub"])

@router.put("/periods/unlock-requests/{request_id}/approve", response_model=UnlockRequestResponse)
async def approve_unlock(request_id: int, approve_in: UnlockApprove, db: Session = Depends(get_db), user: dict = Depends(require_role(["DIRECTOR"]))):
    return await UnlockService.approve_request(db, request_id, approve_in, user["sub"])
