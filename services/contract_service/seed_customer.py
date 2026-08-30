from app.db.session import SessionLocal
from app.models.customer import Customer


CUSTOMERS = [
    {
        "customer_code": "CUS001",
        "tax_code": "0312345678",
        "company_name": "ABC Logistics",
        "representative_name": "Nguyen Van A",
        "email": "contact@abc-logistics.com",
        "phone": "0900000001",
        "address": "Ho Chi Minh City",
        "status": "ACTIVE",
    },
    {
        "customer_code": "CUS002",
        "tax_code": "0312345679",
        "company_name": "XYZ Shipping",
        "representative_name": "Tran Van B",
        "email": "contact@xyz-shipping.com",
        "phone": "0900000002",
        "address": "Ho Chi Minh City",
        "status": "ACTIVE",
    },
    {
        "customer_code": "CUS003",
        "tax_code": "0312345680",
        "company_name": "DEF Transport",
        "representative_name": "Le Van C",
        "email": "contact@def-transport.com",
        "phone": "0900000003",
        "address": "Binh Duong",
        "status": "INACTIVE",
    },
]


def seed_customers():
    db = SessionLocal()

    try:
        for data in CUSTOMERS:
            existing = (
                db.query(Customer)
                .filter(Customer.customer_code == data["customer_code"])
                .first()
            )

            if existing:
                continue

            db.add(Customer(**data))

        db.commit()

    finally:
        db.close()


if __name__ == "__main__":
    seed_customers()