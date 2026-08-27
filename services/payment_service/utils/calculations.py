from decimal import Decimal

from models.payment import PaymentBoard


def calculate_totals(statement: PaymentBoard):
    subtotal = sum((Decimal(item.total_price) for item in statement.items), Decimal("0"))
    tax = subtotal * Decimal(statement.tax_percent) / Decimal("100")
    return subtotal, tax, subtotal + tax
