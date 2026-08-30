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

    @staticmethod
    def get_by_code(
        db: Session,
        customer_code: str,
    ) -> Customer | None:

        return (
            db.query(Customer)
            .filter(
                Customer.customer_code
                == customer_code
            )
            .first()
        )

    @staticmethod
    def get_all(
        db: Session,
        status: str | None = None,
    ) -> list[Customer]:
        query = db.query(Customer)
        if status:
            query = query.filter(Customer.status == status)
        return query.all()