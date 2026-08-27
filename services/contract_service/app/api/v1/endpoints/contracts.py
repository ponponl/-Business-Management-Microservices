from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import (
    CurrentUser,
    get_current_user,
)
from app.db.session import get_db
from app.schemas.contract import (
    CreateContractRequest,
)
from app.services.contract_service import ContractService


router = APIRouter(
    prefix="/contracts",
    tags=["Contracts"],
)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
def create_contract(
    request: CreateContractRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        contract = ContractService.create_contract(
            db=db,
            request=request,
            actor_id=current_user.user_id,
        )

        return contract

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