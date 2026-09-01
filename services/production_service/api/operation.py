from typing import List
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import require_role
from schemas.operation import VolumeCreate, VolumeUpdate, VolumeResponse, UnlockRequestCreate, UnlockApprove, UnlockRequestResponse, BillingSyncResponse
from services.operation_service import OperationService
from services.period_service import PeriodService
from services.unlock_service import UnlockService
from services.integration_service import IntegrationService
from core.idempotency import check_idempotency

router = APIRouter()

@router.post("/volumes", response_model=VolumeResponse, dependencies=[Depends(check_idempotency)])
async def create_volume(volume_in: VolumeCreate, db: Session = Depends(get_db), user: dict = Depends(require_role(["OPERATION_STAFF", "OPERATION_MANAGER", "STAFF", "MANAGER"]))):
    username = user.get("preferred_username") or user.get("username") or user.get("sub")
    return await OperationService.create_volume(db, volume_in, username)

@router.put("/volumes/{volume_id}", response_model=VolumeResponse)
async def update_volume(volume_id: int, volume_in: VolumeUpdate, db: Session = Depends(get_db), user: dict = Depends(require_role(["OPERATION_STAFF", "OPERATION_MANAGER", "STAFF", "MANAGER"]))):
    username = user.get("preferred_username") or user.get("username") or user.get("sub")
    return await OperationService.update_volume(db, volume_id, volume_in, username)

@router.get("/volumes")
def get_volumes(contract_id: str = None, period_key: str = None, db: Session = Depends(get_db), user: dict = Depends(require_role(["OPERATION_STAFF", "OPERATION_MANAGER", "DIRECTOR", "STAFF", "MANAGER"]))):
    return OperationService.get_volumes(db, contract_id, period_key)

@router.get("/contracts")
def get_contracts(db: Session = Depends(get_db), user: dict = Depends(require_role(["OPERATION_STAFF", "OPERATION_MANAGER", "DIRECTOR", "STAFF", "MANAGER"]))):
    return OperationService.get_active_contracts(db)

@router.get("/services")
async def get_services(request: Request, user: dict = Depends(require_role(["OPERATION_STAFF", "OPERATION_MANAGER", "DIRECTOR", "STAFF", "MANAGER"]))):
    auth_header = request.headers.get("Authorization")
    return await IntegrationService.get_pricing_services(auth_header)


@router.get("/volumes/{volume_id}/audit-logs")
def get_audit_logs(volume_id: int, db: Session = Depends(get_db), user: dict = Depends(require_role(["OPERATION_STAFF", "OPERATION_MANAGER", "DIRECTOR", "STAFF", "MANAGER"]))):
    return OperationService.get_audit_logs(db, volume_id)

@router.get("/periods")
def get_periods(db: Session = Depends(get_db), user: dict = Depends(require_role(["OPERATION_MANAGER", "DIRECTOR", "MANAGER"]))):
    return PeriodService.get_periods(db)

@router.post("/periods/{period_key}/lock")
async def lock_period(period_key: str, db: Session = Depends(get_db), user: dict = Depends(require_role(["OPERATION_MANAGER", "MANAGER"]))):
    username = user.get("preferred_username") or user.get("username") or user.get("sub")
    return await PeriodService.lock_period(db, period_key, username)

@router.post("/periods/{period_key}/unlock-request", response_model=UnlockRequestResponse, dependencies=[Depends(check_idempotency)])
def request_unlock(period_key: str, request_in: UnlockRequestCreate, db: Session = Depends(get_db), user: dict = Depends(require_role(["OPERATION_MANAGER", "MANAGER"]))):
    username = user.get("preferred_username") or user.get("username") or user.get("sub")
    return UnlockService.create_request(db, period_key, request_in, username)

@router.get("/periods/unlock-requests")
def get_unlock_requests(db: Session = Depends(get_db), user: dict = Depends(require_role(["DIRECTOR"]))):
    return UnlockService.get_requests(db)

@router.put("/periods/unlock-requests/{request_id}/approve", response_model=UnlockRequestResponse)
async def approve_unlock(request_id: int, approve_in: UnlockApprove, db: Session = Depends(get_db), user: dict = Depends(require_role(["DIRECTOR"]))):
    username = user.get("preferred_username") or user.get("username") or user.get("sub")
    return await UnlockService.approve_request(db, request_id, approve_in, username)

# Lấy dữ liệu cho Payment Service
@router.get("/internal/volumes/billing-sync", response_model=List[BillingSyncResponse])
def get_billing_volumes(
    contract_id: str = None, 
    period_start: str = None, 
    period_end: str = None, 
    service_code: str = None, 
    db: Session = Depends(get_db)
):
    return OperationService.get_billing_volumes(
        db, contract_id, period_start, period_end, service_code
    )
