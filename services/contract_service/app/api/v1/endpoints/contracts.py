from uuid import UUID
from fastapi.responses import JSONResponse

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
    Header,
)

from sqlalchemy.orm import Session

from app.core.dependencies import (
    CurrentUser,
    get_current_user,
)

from app.db.session import get_db

from app.schemas.contract import (
    CreateContractRequest,
    ContractResponse,
    ContractListResponse,
    UpdateContractRequest,
    RenewContractRequest,
    CancelContractRequest,
    StartReviewRequest,
    ApprovalActionRequest,
)

from app.schemas.payment_validation import (
    PaymentContractValidationRequest,
    PaymentContractValidationResponse,
)

from app.services.contract_service import (
    ContractService,
)

from app.services.approval_service import (
    ApprovalService,
)

router = APIRouter(
    prefix="/contracts",
    tags=["Contracts"],
)

@router.post(
    "",
    response_model=ContractResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_contract(
    request: CreateContractRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):

    try:

        contract = ContractService.create_contract(
            db=db,
            request=request,
            actor_id=UUID(
                current_user.user_id
            ),
        )

        contract, version = (
            ContractService.get_contract(
                db,
                contract.contract_id,
            )
        )

        return {
            "contract_id": contract.contract_id,
            "contract_number": contract.contract_number,
            "customer_id": contract.customer_id,
            "current_version": contract.current_version,
            "status": contract.status,
            "row_version": contract.row_version,
            "created_at": contract.created_at,
            "updated_at": contract.updated_at,
            "current_version_detail": version,
        }

    except ValueError as exc:

        code = str(exc)

        if code == "CUSTOMER_NOT_FOUND":
            raise HTTPException(
                status_code=404,
                detail=code,
            )

        if code == "CUSTOMER_INACTIVE":
            raise HTTPException(
                status_code=422,
                detail=code,
            )

        raise HTTPException(
            status_code=400,
            detail=code,
        )
        

@router.get(
    "/{contract_id}",
    response_model=ContractResponse,
)
def get_contract(
    contract_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):

    try:

        contract, version = (
            ContractService.get_contract(
                db,
                contract_id,
            )
        )

        return {
            "contract_id": contract.contract_id,
            "contract_number": contract.contract_number,
            "customer_id": contract.customer_id,
            "current_version": contract.current_version,
            "status": contract.status,
            "row_version": contract.row_version,
            "created_at": contract.created_at,
            "updated_at": contract.updated_at,
            "current_version_detail": version,
        }

    except ValueError as exc:

        code = str(exc)

        if code == "CONTRACT_NOT_FOUND":
            raise HTTPException(
                status_code=404,
                detail=code,
            )

        if code == "CURRENT_VERSION_NOT_FOUND":
            raise HTTPException(
                status_code=500,
                detail=code,
            )

        raise HTTPException(
            status_code=400,
            detail=code,
        )

@router.get(
    "",
    response_model=ContractListResponse,
)
def list_contracts(
    customer_id: UUID | None = None,

    status: str | None = None,

    skip: int = Query(
        default=0,
        ge=0,
    ),

    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),

    db: Session = Depends(get_db),

    current_user: CurrentUser = Depends(
        get_current_user
    ),
):

    contracts, total = (
        ContractService.list_contracts(
            db=db,
            customer_id=customer_id,
            status=status,
            skip=skip,
            limit=limit,
        )
    )

    return {
        "items": contracts,
        "total": total,
        "skip": skip,
        "limit": limit,
    }
    
@router.put(
    "/{contract_id}",
    response_model=ContractResponse,
)
def update_contract(
    contract_id: UUID,
    request: UpdateContractRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):

    try:

        actor_id = UUID(
            current_user.user_id
        )

        contract = ContractService.update_contract(
            db=db,
            contract_id=contract_id,
            request=request,
            actor_id=actor_id,
        )

        contract, version = (
            ContractService.get_contract(
                db,
                contract.contract_id,
            )
        )

        return {
            "contract_id": contract.contract_id,
            "contract_number": contract.contract_number,
            "customer_id": contract.customer_id,
            "current_version": contract.current_version,
            "status": contract.status,
            "row_version": contract.row_version,
            "created_at": contract.created_at,
            "updated_at": contract.updated_at,
            "current_version_detail": version,
        }

    except ValueError as exc:

        code = str(exc)

        if code == "CONTRACT_NOT_FOUND":
            raise HTTPException(
                status_code=404,
                detail=code,
            )

        if code == "INVALID_STATE":
            raise HTTPException(
                status_code=409,
                detail=code,
            )

        if code == "VERSION_CONFLICT":
            raise HTTPException(
                status_code=409,
                detail=code,
            )

        raise HTTPException(
            status_code=400,
            detail=code,
        )

# submit contract endpoint
@router.post(
    "/{contract_id}/submit",
)
def submit_contract(
    contract_id: UUID,
    idempotency_key: str = Header(
        ...,
        alias="Idempotency-Key",
        description="Unique key to prevent duplicate submissions",
    ),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        actor_id = UUID(current_user.user_id)

        response_status, response_body = ContractService.submit_contract(
            db=db,
            contract_id=contract_id,
            idempotency_key=idempotency_key,
            actor_id=actor_id,
        )

        return JSONResponse(
            status_code=response_status,
            content=response_body,
        )

    except ValueError as exc:
        code = str(exc)

        if code in {"CONTRACT_NOT_FOUND", "CUSTOMER_NOT_FOUND"}:
            raise HTTPException(
                status_code=404,
                detail=code,
            )

        if code == "CUSTOMER_INACTIVE":
            raise HTTPException(
                status_code=422,
                detail=code,
            )

        if code in {"INVALID_STATE", "IDEMPOTENCY_KEY_REUSED"}:
            raise HTTPException(
                status_code=409,
                detail=code,
            )

        if code == "CURRENT_VERSION_NOT_FOUND":
            raise HTTPException(
                status_code=500,
                detail=code,
            )

        raise HTTPException(
            status_code=400,
            detail=code,
        )
        
# renew contract endpoint
@router.post(
    "/{contract_id}/renew",
)
def renew_contract(
    contract_id: UUID,
    request: RenewContractRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):

    try:
        actor_id = UUID(
            current_user.user_id
        )

        contract = ContractService.renew_contract(
            db=db,
            contract_id=contract_id,
            request=request,
            actor_id=actor_id,
        )

        return {
            "contract_id":
                str(contract.contract_id),

            "contract_number":
                contract.contract_number,

            "current_version":
                contract.current_version,

            "row_version":
                contract.row_version,

            "status":
                contract.status,

            "message":
                "Contract renewed successfully",
        }

    except ValueError as exc:

        code = str(exc)

        if code == "CONTRACT_NOT_FOUND":
            raise HTTPException(
                status_code=404,
                detail=code,
            )

        if code == "RENEW_NOT_ALLOWED":
            raise HTTPException(
                status_code=409,
                detail=code,
            )

        if code == "CURRENT_VERSION_NOT_FOUND":
            raise HTTPException(
                status_code=500,
                detail=code,
            )

        if code == "INVALID_RENEWAL_DATE":
            raise HTTPException(
                status_code=422,
                detail=code,
            )

        raise HTTPException(
            status_code=400,
            detail=code,
        )
        

# cancel contract endpoint
@router.post(
    "/{contract_id}/cancel",
)
def cancel_contract(
    contract_id: UUID,
    request: CancelContractRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):

    try:

        actor_id = UUID(
            current_user.user_id
        )

        contract = (
            ContractService.cancel_contract(
                db=db,
                contract_id=contract_id,
                request=request,
                actor_id=actor_id,
            )
        )

        return {
            "contract_id":
                str(contract.contract_id),

            "contract_number":
                contract.contract_number,

            "status":
                contract.status,

            "row_version":
                contract.row_version,

            "message":
                "Contract cancelled successfully",
        }

    except ValueError as exc:

        code = str(exc)

        if code == "CONTRACT_NOT_FOUND":
            raise HTTPException(
                status_code=404,
                detail=code,
            )

        if code == "CANCEL_NOT_ALLOWED":
            raise HTTPException(
                status_code=409,
                detail=code,
            )

        raise HTTPException(
            status_code=400,
            detail=code,
        )
        

@router.post(
    "/{contract_id}/start-review",
)
def start_review(
    contract_id: UUID,
    request: StartReviewRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):

    try:

        contract = (
            ApprovalService.start_review(
                db=db,
                contract_id=contract_id,
                approver_id=request.approver_id,
                actor_id=UUID(
                    current_user.user_id
                ),
            )
        )

        return {
            "contract_id":
                str(contract.contract_id),

            "contract_number":
                contract.contract_number,

            "status":
                contract.status,

            "message":
                "Contract submitted for review",
        }

    except ValueError as exc:

        code = str(exc)

        if code == "CONTRACT_NOT_FOUND":
            raise HTTPException(
                status_code=404,
                detail=code,
            )

        if code == "INVALID_STATE":
            raise HTTPException(
                status_code=409,
                detail=code,
            )

        if code == "APPROVAL_ALREADY_EXISTS":
            raise HTTPException(
                status_code=409,
                detail=code,
            )

        raise HTTPException(
            status_code=400,
            detail=code,
        )
      
      
# approve contract endpoint       
@router.post(
    "/{contract_id}/approve",
)
def approve_contract(
    contract_id: UUID,
    request: ApprovalActionRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):

    try:

        contract = ApprovalService.approve(
            db=db,
            contract_id=contract_id,
            actor_id=UUID(
                current_user.user_id
            ),
            comment=request.comment,
        )

        return {
            "contract_id":
                str(contract.contract_id),

            "contract_number":
                contract.contract_number,

            "status":
                contract.status,

            "row_version":
                contract.row_version,

            "message":
                "Contract approved successfully",
        }

    except ValueError as exc:

        code = str(exc)

        if code == "CONTRACT_NOT_FOUND":
            raise HTTPException(
                status_code=404,
                detail=code,
            )

        if code == "INVALID_STATE":
            raise HTTPException(
                status_code=409,
                detail=code,
            )

        if code == "APPROVAL_NOT_FOUND":
            raise HTTPException(
                status_code=409,
                detail=code,
            )

        if code == "APPROVAL_ALREADY_PROCESSED":
            raise HTTPException(
                status_code=409,
                detail=code,
            )

        if code == "NOT_ASSIGNED_APPROVER":
            raise HTTPException(
                status_code=403,
                detail=code,
            )

        raise HTTPException(
            status_code=400,
            detail=code,
        )


@router.post(
    "/{contract_id}/reject",
)
def reject_contract(
    contract_id: UUID,
    request: ApprovalActionRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):

    try:

        contract = ApprovalService.reject(
            db=db,
            contract_id=contract_id,
            actor_id=UUID(
                current_user.user_id
            ),
            comment=request.comment,
        )

        return {
            "contract_id":
                str(contract.contract_id),

            "contract_number":
                contract.contract_number,

            "status":
                contract.status,

            "row_version":
                contract.row_version,

            "message":
                "Contract rejected successfully",
        }

    except ValueError as exc:

        code = str(exc)

        if code == "CONTRACT_NOT_FOUND":
            raise HTTPException(
                status_code=404,
                detail=code,
            )

        if code == "INVALID_STATE":
            raise HTTPException(
                status_code=409,
                detail=code,
            )

        if code == "APPROVAL_NOT_FOUND":
            raise HTTPException(
                status_code=409,
                detail=code,
            )

        if code == "APPROVAL_ALREADY_PROCESSED":
            raise HTTPException(
                status_code=409,
                detail=code,
            )

        if code == "NOT_ASSIGNED_APPROVER":
            raise HTTPException(
                status_code=403,
                detail=code,
            )

        if code == "COMMENT_REQUIRED":
            raise HTTPException(
                status_code=422,
                detail=code,
            )

        raise HTTPException(
            status_code=400,
            detail=code,
        )
        
@router.post(
    "/{contract_id}/request-revision",
)
def request_revision(
    contract_id: UUID,
    request: ApprovalActionRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):

    try:

        contract = (
            ApprovalService.request_revision(
                db=db,
                contract_id=contract_id,
                actor_id=UUID(
                    current_user.user_id
                ),
                comment=request.comment,
            )
        )

        return {
            "contract_id":
                str(contract.contract_id),

            "contract_number":
                contract.contract_number,

            "status":
                contract.status,

            "row_version":
                contract.row_version,

            "message":
                "Contract revision requested",
        }

    except ValueError as exc:

        code = str(exc)

        if code == "CONTRACT_NOT_FOUND":
            raise HTTPException(
                status_code=404,
                detail=code,
            )

        if code == "INVALID_STATE":
            raise HTTPException(
                status_code=409,
                detail=code,
            )

        if code == "APPROVAL_NOT_FOUND":
            raise HTTPException(
                status_code=409,
                detail=code,
            )

        if code == "APPROVAL_ALREADY_PROCESSED":
            raise HTTPException(
                status_code=409,
                detail=code,
            )

        if code == "NOT_ASSIGNED_APPROVER":
            raise HTTPException(
                status_code=403,
                detail=code,
            )

        if code == "COMMENT_REQUIRED":
            raise HTTPException(
                status_code=422,
                detail=code,
            )

        raise HTTPException(
            status_code=400,
            detail=code,
        )
        
# Validate contract for payment endpoint
@router.post(
    "/validate-for-payment",
    response_model=PaymentContractValidationResponse,
)
def validate_for_payment(
    request: PaymentContractValidationRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    return ContractService.validate_for_payment(
        db=db,
        contract_id=request.contract_id,
        customer_id=request.customer_id,
        billing_period_start=(
            request.billing_period_start
        ),
        billing_period_end=(
            request.billing_period_end
        ),
    )