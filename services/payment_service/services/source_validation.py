from decimal import Decimal

from fastapi import HTTPException

from schemas.payment import PaymentBoardInput
from utils.http_client import call_json


PRICING_SERVICE_URL = "http://pricing-service:8000"
PRODUCTION_SERVICE_URL = "http://production-service:8000"
CONTRACT_SERVICE_URL = "http://contract-service:8000"


def validate_payment_sources(payload: PaymentBoardInput, authorization: str | None):
    contract_result = call_json(
        "GET",
        f"{CONTRACT_SERVICE_URL}/api/v1/contracts/{payload.contract_id}/payment-validation",
        query={
            "customer_id": payload.customer_id,
            "period_start": payload.period_start.isoformat(),
            "period_end": payload.period_end.isoformat(),
        },
        authorization=authorization,
    )
    if not contract_result.get("valid"):
        raise HTTPException(422, contract_result.get("reason", "Hợp đồng không hợp lệ"))
    
    price_result = call_json(
        "POST",
        f"{PRICING_SERVICE_URL}/api/v1/payment-integration/validate-for-payment",
        payload={
            "price_table_id": payload.price_table_id,
            "customer_id": payload.customer_id,
            "contract_id": payload.contract_id,
            "period_start": payload.period_start.isoformat(),
            "period_end": payload.period_end.isoformat(),
        },
        authorization=authorization,
    )
    if not price_result.get("is_valid"):
        raise HTTPException(422, price_result.get("message", "Bảng giá không hợp lệ"))

    period_key = payload.period_start.strftime("%Y-%m")
    if payload.period_end.strftime("%Y-%m") != period_key:
        raise HTTPException(422, "Kỳ thanh toán phải nằm trong cùng một tháng theo Production")
    volume_rows = call_json(
        "GET", f"{PRODUCTION_SERVICE_URL}/api/v1/volumes",
        query={"customer_id": payload.customer_id, "contract_id": payload.contract_id, "period_key": period_key},
        authorization=authorization,
    )
    if not isinstance(volume_rows, list) or not volume_rows:
        raise HTTPException(422, "Không có sản lượng cho kỳ thanh toán đã chọn")
    if not all(row.get("is_locked") for row in volume_rows):
        raise HTTPException(422, "Sản lượng chưa được khóa/đối soát")

    volumes = {}
    for row in volume_rows:
        code = row.get("service_code")
        if code:
            current = volumes.setdefault(code, {"quantity": Decimal("0"), "unit": row.get("unit") or ""})
            current["quantity"] += Decimal(str(row.get("quantity") or 0))
    prices = {item["service_code"]: item for item in price_result.get("items", [])}
    missing = [item.service_code for item in payload.items if item.service_code not in volumes]
    if missing:
        raise HTTPException(422, f"Thiếu sản lượng cho dịch vụ: {', '.join(missing)}")
    return [{
        "service_code": item.service_code,
        "service_name": prices.get(item.service_code, {}).get("service_name", item.service_name),
        "unit": volumes[item.service_code]["unit"] or item.unit,
        "quantity": volumes[item.service_code]["quantity"],
        "unit_price": Decimal(str(prices.get(item.service_code, {}).get("unit_price", item.unit_price))),
    } for item in payload.items]
