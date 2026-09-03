from datetime import date
from uuid import UUID
from fastapi.responses import FileResponse, JSONResponse
import json

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
    Header,
    File,
    Form,
    UploadFile,
)

from sqlalchemy.orm import Session

from app.core.dependencies import (
    CurrentUser,
    get_current_user,
)

from app.db.session import get_db
from app.models.contract_attachment import ContractAttachment
from app.models.contract_version import ContractVersion
from app.services.file_storage import storage

from app.schemas.contract import (
    CreateContractRequest,
    ContractResponse,
    ContractListResponse,
    UpdateContractRequest,
    RenewContractRequest,
    CancelContractRequest,
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


# create contract endpoint
@router.post(
    "",
    response_model=ContractResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_contract(
    contract: str = Form(...),

    attachments: list[UploadFile] = File(
    default_factory=list
    ),

    db: Session = Depends(get_db),

    current_user: CurrentUser = Depends(
        get_current_user
    ),
):

    try:

        # -------------------------------------------------
        # Parse contract JSON
        # -------------------------------------------------

        try:

            contract_dict = json.loads(
                contract
            )

        except json.JSONDecodeError:

            raise HTTPException(
                status_code=422,
                detail={
                    "code": "INVALID_CONTRACT_JSON",
                    "message": (
                        "Contract JSON không hợp lệ."
                    ),
                },
            )

        # -------------------------------------------------
        # Validate Pydantic schema
        # -------------------------------------------------

        request = (
            CreateContractRequest.model_validate(
                contract_dict
            )
        )

        # -------------------------------------------------
        # Create
        # -------------------------------------------------

        return await ContractService.create_contract(
            db=db,
            request=request,
            actor_id=UUID(
                current_user.user_id
            ),
            attachments=attachments,
        )

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

        if code in {
            "INVALID_FILE_NAME",
            "DUPLICATE_FILE_NAME",
        }:
            raise HTTPException(
                status_code=422,
                detail=code,
            )

        raise HTTPException(
            status_code=400,
            detail=code,
        )
        
# get contract by ID endpoint
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
            "contract_id": (
                contract.contract_id
            ),
            "contract_number": (
                contract.contract_number
            ),
            "customer_id": (
                contract.customer_id
            ),
            "current_version": (
                contract.current_version
            ),
            "status": contract.status,
            "row_version": (
                contract.row_version
            ),
            "created_at": (
                contract.created_at
            ),
            "updated_at": (
                contract.updated_at
            ),
            "current_version_detail": version,
            "attachments": (
                version.attachments
            ),
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
    "/{contract_id}/attachments/{attachment_id}",
)
def download_contract_attachment(
    contract_id: UUID,
    attachment_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    attachment = (
        db.query(ContractAttachment)
        .join(ContractVersion, ContractVersion.version_id == ContractAttachment.version_id)
        .filter(
            ContractAttachment.attachment_id == attachment_id,
            ContractVersion.contract_id == contract_id,
        )
        .first()
    )

    if attachment is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "ATTACHMENT_NOT_FOUND",
                "message": "File đính kèm không tồn tại.",
            },
        )

    file_path = storage.resolve_path(attachment.object_key)

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail={
                "code": "ATTACHMENT_FILE_NOT_FOUND",
                "message": "File đính kèm đã bị mất trên hệ thống.",
            },
        )

    return FileResponse(
        path=str(file_path),
        media_type=attachment.content_type or "application/octet-stream",
        filename=attachment.file_name,
    )

# list contracts endpoint
@router.get(
    "",
    response_model=ContractListResponse,
)
def list_contracts(
    customer_id: UUID | None = Query(
        default=None
    ),

    status_filter: str | None = Query(
        default=None,
        alias="status",
    ),

    skip: int = Query(
        default=0,
        ge=0,
    ),

    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),

    search: str | None = Query(default=None, max_length=100),

    effective_date: date | None = Query(default=None),

    db: Session = Depends(get_db),

    current_user: CurrentUser = Depends(
        get_current_user
    ),
):

    items, total, summary = (
        ContractService.list_contracts(
            db=db,
            customer_id=customer_id,
            status=status_filter,
            search=search,
            effective_date=effective_date,
            skip=skip,
            limit=limit,
        )
    )

    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
        "summary": summary,
    }

# Update contract endpoint
@router.put(
    "/{contract_id}",
    response_model=ContractResponse,
)
async def update_contract(
    contract_id: UUID,

    contract: str = Form(...),

    attachments: list[UploadFile] = File(
    default_factory=list
    ),

    db: Session = Depends(get_db),

    current_user: CurrentUser = Depends(
        get_current_user
    ),
):

    try:

        # -------------------------------------------------
        # Parse contract JSON
        # -------------------------------------------------

        try:

            contract_dict = json.loads(
                contract
            )

        except json.JSONDecodeError:

            raise HTTPException(
                status_code=422,
                detail={
                    "code": "INVALID_CONTRACT_JSON",
                    "message": (
                        "Contract JSON không hợp lệ."
                    ),
                },
            )

        # -------------------------------------------------
        # Validate Pydantic schema
        # -------------------------------------------------

        request = (
            UpdateContractRequest.model_validate(
                contract_dict
            )
        )

        # -------------------------------------------------
        # Update
        # -------------------------------------------------

        return await ContractService.update_contract(
            db=db,
            contract_id=contract_id,
            request=request,
            actor_id=UUID(
                current_user.user_id
            ),
            attachments=attachments,
        )

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

        if code in {
            "INVALID_FILE_NAME",
            "DUPLICATE_FILE_NAME",
        }:
            raise HTTPException(
                status_code=422,
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
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    try:
        actor_id = UUID(
            current_user.user_id
        )

        response_status, response_body = (
            ContractService.submit_contract(
                db=db,
                contract_id=contract_id,
                idempotency_key=idempotency_key,
                actor_id=actor_id,
            )
        )

        return JSONResponse(
            status_code=response_status,
            content=response_body,
        )

    except ValueError as exc:
        code = str(exc)

        if code in {
            "CONTRACT_NOT_FOUND",
            "CUSTOMER_NOT_FOUND",
        }:
            raise HTTPException(
                status_code=404,
                detail=code,
            )

        if code in {
            "CUSTOMER_INACTIVE",
            "ATTACHMENT_REQUIRED",
            "INVALID_EFFECTIVE_PERIOD",
        }:
            raise HTTPException(
                status_code=422,
                detail=code,
            )

        if code in {
            "INVALID_STATE",
            "IDEMPOTENCY_KEY_REUSED",
        }:
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
        
# =========================================================
# START REVIEW
# =========================================================
@router.post(
    "/{contract_id}/start-review",
)
def start_review(
    contract_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):

    try:
        actor_id = UUID(
            current_user.user_id
        )

        contract = ApprovalService.start_review(
            db=db,
            contract_id=contract_id,
            actor_id=actor_id,
            actor_role=current_user.role,
        )

        if current_user.role == "MANAGER":
            message = "Manager review started"
        else:
            message = "Director review started"

        return {
            "contract_id": str(
                contract.contract_id
            ),
            "contract_number":
                contract.contract_number,
            "status":
                contract.status,
            "message":
                message,
        }

    except ValueError as exc:
        code = str(exc)

        if code == "CONTRACT_NOT_FOUND":
            raise HTTPException(
                status_code=404,
                detail=code,
            )

        if code == "FORBIDDEN":
            raise HTTPException(
                status_code=403,
                detail=code,
            )

        if code in {
            "INVALID_STATE",
            "APPROVAL_ALREADY_EXISTS",
            "APPROVAL_NOT_FOUND",
            "MANAGER_APPROVAL_REQUIRED",
        }:
            raise HTTPException(
                status_code=409,
                detail=code,
            )

        raise HTTPException(
            status_code=400,
            detail=code,
        )
        
# =========================================================
# APPROVE CONTRACT
# =========================================================
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
            actor_role=current_user.role,
            comment=request.comment,
        )

        message = (
            "Manager approved successfully"
            if current_user.role == "MANAGER"
            else "Director approved successfully"
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
                message,
        }

    except ValueError as exc:
        code = str(exc)

        if code == "CONTRACT_NOT_FOUND":
            raise HTTPException(
                status_code=404,
                detail=code,
            )

        if code == "FORBIDDEN":
            raise HTTPException(
                status_code=403,
                detail=code,
            )

        if code in {
            "INVALID_STATE",
            "APPROVAL_NOT_FOUND",
            "APPROVAL_ALREADY_PROCESSED",
        }:
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
        
# =========================================================
# REJECT CONTRACT
# =========================================================
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
            actor_role=current_user.role,
            comment=request.comment,
        )

        message = (
            "Manager rejected the contract"
            if current_user.role == "MANAGER"
            else "Director rejected the contract"
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
                message,
        }

    except ValueError as exc:
        code = str(exc)

        if code == "CONTRACT_NOT_FOUND":
            raise HTTPException(
                status_code=404,
                detail=code,
            )

        if code == "FORBIDDEN":
            raise HTTPException(
                status_code=403,
                detail=code,
            )

        if code in {
            "INVALID_STATE",
            "APPROVAL_NOT_FOUND",
            "APPROVAL_ALREADY_PROCESSED",
        }:
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
        
# =========================================================
# REQUEST REVISION
# =========================================================
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
        contract = ApprovalService.request_revision(
            db=db,
            contract_id=contract_id,
            actor_id=UUID(
                current_user.user_id
            ),
            actor_role=current_user.role,
            comment=request.comment,
        )

        message = (
            "Manager requested revision"
            if current_user.role == "MANAGER"
            else "Director requested revision"
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
                message,
        }

    except ValueError as exc:
        code = str(exc)

        if code == "CONTRACT_NOT_FOUND":
            raise HTTPException(
                status_code=404,
                detail=code,
            )

        if code == "FORBIDDEN":
            raise HTTPException(
                status_code=403,
                detail=code,
            )

        if code in {
            "INVALID_STATE",
            "APPROVAL_NOT_FOUND",
            "APPROVAL_ALREADY_PROCESSED",
        }:
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
        
# =========================================================
# FORWARD DIRECTOR REVISION TO STAFF
# =========================================================
@router.post(
    "/{contract_id}/forward-revision",
)
def forward_revision(
    contract_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):

    try:
        contract = ApprovalService.forward_revision(
            db=db,
            contract_id=contract_id,
            actor_id=UUID(
                current_user.user_id
            ),
            actor_role=current_user.role,
        )

        return {
            "contract_id":
                str(contract.contract_id),
            "contract_number":
                contract.contract_number,
            "status":
                contract.status,
            "message":
                "Director revision forwarded to Staff",
        }

    except ValueError as exc:
        code = str(exc)

        if code == "CONTRACT_NOT_FOUND":
            raise HTTPException(
                status_code=404,
                detail=code,
            )

        if code == "FORBIDDEN":
            raise HTTPException(
                status_code=403,
                detail=code,
            )

        if code in {
            "INVALID_STATE",
            "APPROVAL_NOT_FOUND",
            "INVALID_REVISION_SOURCE",
            "REVISION_ALREADY_FORWARDED",
        }:
            raise HTTPException(
                status_code=409,
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