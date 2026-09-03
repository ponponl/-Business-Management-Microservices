from typing import List
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import require_role, get_username
from schemas.operation import VolumeCreate, VolumeUpdate, VolumeResponse, UnlockRequestCreate, UnlockApprove, UnlockRequestResponse, BillingSyncResponse
from services.operation_service import OperationService
from services.period_service import PeriodService
from services.unlock_service import UnlockService
from services.integration_service import IntegrationService
from core.idempotency import IdempotentRoute

router = APIRouter()
idempotent_router = APIRouter(route_class=IdempotentRoute)

@idempotent_router.post("/volumes", response_model=VolumeResponse)
async def create_volume(volume_in: VolumeCreate, db: Session = Depends(get_db), user: dict = Depends(require_role(["STAFF", "MANAGER"]))):
    username = get_username(user)
    return await OperationService.create_volume(db, volume_in, username)

@router.put("/volumes/{volume_id}", response_model=VolumeResponse)
async def update_volume(volume_id: int, volume_in: VolumeUpdate, db: Session = Depends(get_db), user: dict = Depends(require_role(["STAFF", "MANAGER"]))):
    username = get_username(user)
    return await OperationService.update_volume(db, volume_id, volume_in, username)

@router.get("/volumes")
def get_volumes(contract_id: str = None, period_key: str = None, db: Session = Depends(get_db), user: dict = Depends(require_role(["STAFF", "MANAGER"]))):
    return OperationService.get_volumes(db, contract_id, period_key)

@router.get("/contracts")
def get_contracts(db: Session = Depends(get_db), user: dict = Depends(require_role(["STAFF", "MANAGER"]))):
    return OperationService.get_active_contracts(db)

@router.get("/contracts/{contract_id}/services")
async def get_services_by_contract(contract_id: str, request: Request, user: dict = Depends(require_role(["STAFF", "MANAGER"]))):
    auth_header = request.headers.get("Authorization")
    return await IntegrationService.get_pricing_services_by_contract(contract_id, auth_header)


@router.get("/volumes/{volume_id}/audit-logs")
def get_audit_logs(volume_id: int, db: Session = Depends(get_db), user: dict = Depends(require_role(["STAFF", "MANAGER"]))):
    return OperationService.get_audit_logs(db, volume_id)

@router.get("/periods")
def get_periods(db: Session = Depends(get_db), user: dict = Depends(require_role(["STAFF", "MANAGER"]))):
    return PeriodService.get_periods(db)

@router.post("/periods/{period_key}/lock")
async def lock_period(period_key: str, db: Session = Depends(get_db), user: dict = Depends(require_role(["STAFF", "MANAGER"]))):
    username = get_username(user)
    return await PeriodService.lock_period(db, period_key, username)

@idempotent_router.post("/periods/{period_key}/unlock-request", response_model=UnlockRequestResponse)
def request_unlock(period_key: str, request_in: UnlockRequestCreate, db: Session = Depends(get_db), user: dict = Depends(require_role(["STAFF", "MANAGER"]))):
    username = get_username(user)
    return UnlockService.create_request(db, period_key, request_in, username)

@router.get("/periods/unlock-requests")
def get_unlock_requests(db: Session = Depends(get_db), user: dict = Depends(require_role(["DIRECTOR"]))):
    return UnlockService.get_requests(db)

@router.put("/periods/unlock-requests/{request_id}/approve", response_model=UnlockRequestResponse)
async def approve_unlock(request_id: int, approve_in: UnlockApprove, db: Session = Depends(get_db), user: dict = Depends(require_role(["DIRECTOR"]))):
    username = get_username(user)
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

router.include_router(idempotent_router)
