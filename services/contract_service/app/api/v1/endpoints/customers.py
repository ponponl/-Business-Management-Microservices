from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import CurrentUser, get_current_user
from app.db.session import get_db
from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer import CustomerResponse

router = APIRouter(
    prefix="/customers",
    tags=["Customers"],
)

@router.get(
    "",
    response_model=list[CustomerResponse],
)
def list_customers(
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    customers = CustomerRepository.get_all(db=db, status=status)
    return customers
