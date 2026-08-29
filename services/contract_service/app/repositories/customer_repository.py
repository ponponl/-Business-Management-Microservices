from uuid import UUID

from sqlalchemy.orm import Session

from app.models.customer import Customer


class CustomerRepository:

    @staticmethod
    def get_by_id(
        db: Session,
        customer_id: UUID,
    ) -> Customer | None:
        return (
            db.query(Customer)
            .filter(
                Customer.customer_id == customer_id
            )
            .first()
        )