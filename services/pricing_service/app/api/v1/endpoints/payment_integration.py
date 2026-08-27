from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.payment_integration import PaymentValidationRequest, PaymentValidationResponse
from app.services.payment_integration_service import PaymentIntegrationService

router = APIRouter()


@router.post(
    "/validate-for-payment",
    response_model=PaymentValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Xác thực điều kiện bảng giá cho Payment Service"
)
def validate_price_list_for_payment(
    payload: PaymentValidationRequest,
    db: Session = Depends(get_db)
):
    """Xác thực bảng giá và lấy danh sách chi tiết đơn giá cho Payment Service."""
    return PaymentIntegrationService.validate_price_list_for_payment(db, payload)