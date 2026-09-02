from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.contract_integration import ContractServicesResponse
from app.services.contract_integration_service import ContractIntegrationService

router = APIRouter()


@router.get(
    "/{contract_id}/services",
    response_model=ContractServicesResponse,
    summary="Lấy danh sách dịch vụ theo Mã Hợp đồng"
)
def get_services_by_contract(
    contract_id: str = Path(..., description="Mã Hợp đồng (VD: CTR-SEED-001)"),
    db: Session = Depends(get_db)
):
    """
    API hỗ trợ Production Service: Truy vấn danh sách dịch vụ và đơn giá áp dụng dựa trên contract_id.
    """
    return ContractIntegrationService.get_services_by_contract(db=db, contract_id=contract_id)