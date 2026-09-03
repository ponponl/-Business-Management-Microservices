from decimal import Decimal

from fastapi import HTTPException

from schemas.payment import PaymentBoardInput
from utils.http_client import call_json


PRICING_SERVICE_URL = "http://pricing-service:8000"
PRODUCTION_SERVICE_URL = "http://production-service:8000"
CONTRACT_SERVICE_URL = "http://contract-service:8000"


def validate_payment_sources(payload: PaymentBoardInput, authorization: str | None):
    contract_id = payload.contract_id
    contracts = call_json(
        "GET",
        f"{CONTRACT_SERVICE_URL}/api/v1/contracts",
        authorization=authorization,
    )
    contract_rows = contracts.get("items", contracts) if isinstance(contracts, dict) else contracts
    matching_contract = next(
        (item for item in contract_rows if item.get("contract_number") == payload.contract_id),
        None,
    )
    if matching_contract:
        contract_id = matching_contract["contract_id"]

    contract_result = call_json(
        "POST",
        f"{CONTRACT_SERVICE_URL}/api/v1/contracts/validate-for-payment",
        payload={
            "contract_id": contract_id,
            "customer_id": payload.customer_id,
            "billing_period_start": payload.period_start.isoformat(),
            "billing_period_end": payload.period_end.isoformat(),
        },
        authorization=authorization,
    )
    if not contract_result.get("valid"):
        raise HTTPException(422, contract_result.get("reason", "Hợp đồng không hợp lệ"))
    
    period_key = payload.period_id or payload.period_start.strftime("%Y-%m")
    if payload.period_id and payload.period_id != payload.period_start.strftime("%Y-%m"):
        raise HTTPException(422, "Kỳ sản lượng không khớp với khoảng ngày đã chọn")
    if payload.period_end.strftime("%Y-%m") != period_key:
        raise HTTPException(422, "Kỳ thanh toán phải nằm trong cùng một tháng theo Production")
    volume_rows = call_json(
        "GET", f"{PRODUCTION_SERVICE_URL}/api/v1/internal/volumes/billing-sync",
        query={"period_key": period_key},
        authorization=authorization,
    )
    volume_rows = [
        row for row in volume_rows
        if str(row.get("contract_id")) == payload.contract_id
        and row.get("period_key") == period_key
        and payload.period_start.isoformat() <= str(row.get("volume_date", "")) <= payload.period_end.isoformat()
    ]
    if not isinstance(volume_rows, list) or not volume_rows:
        raise HTTPException(422, "Không có sản lượng cho kỳ thanh toán đã chọn")
    if not all(row.get("is_locked") and row.get("period_status") == "LOCKED" for row in volume_rows):
        raise HTTPException(422, "Sản lượng chưa được khóa/đối soát")

    operation_dates = sorted({str(row.get("volume_date", ""))[:10] for row in volume_rows})
    service_codes = sorted({row.get("service_code") for row in volume_rows if row.get("service_code")})
    price_result = call_json(
        "POST", f"{PRICING_SERVICE_URL}/api/v1/payment-integration/resolve-for-payment",
        payload={
            "customer_id": payload.customer_id,
            "contract_id": contract_id,
            "operation_dates": operation_dates,
            "service_codes": service_codes,
        }, authorization=authorization,
    )
    prices = {(item["operation_date"], item["service_code"]): item for item in price_result.get("items", [])}

    volumes = {}
    for row in volume_rows:
        code = row.get("service_code")
        if code:
            operation_date = str(row.get("volume_date", ""))[:10]
            current = volumes.setdefault((operation_date, code), {"quantity": Decimal("0"), "unit": row.get("unit") or ""})
            current["quantity"] += Decimal(str(row.get("quantity") or 0))
    missing = [f"{item.operation_date or payload.period_start}:{item.service_code}" for item in payload.items if (str(item.operation_date or payload.period_start), item.service_code) not in volumes]
    if missing:
        raise HTTPException(422, f"Thiếu sản lượng cho dịch vụ: {', '.join(missing)}")
    missing_prices = [f"{key[0]}:{key[1]}" for key in volumes if key not in prices]
    if missing_prices:
        raise HTTPException(422, f"Chưa có đơn giá cho: {', '.join(missing_prices)}")
    return {
        "items": [{
            "service_code": item.service_code,
            "service_name": prices[(str(item.operation_date or payload.period_start), item.service_code)]["service_name"],
            "unit": volumes[(str(item.operation_date or payload.period_start), item.service_code)]["unit"] or item.unit,
            "quantity": volumes[(str(item.operation_date or payload.period_start), item.service_code)]["quantity"],
            "unit_price": Decimal(str(prices[(str(item.operation_date or payload.period_start), item.service_code)]["unit_price"])),
            "operation_date": item.operation_date or payload.period_start,
        } for item in payload.items],
        "price_list_id": "MULTIPLE" if len({item["price_list_id"] for item in prices.values()}) > 1 else next(iter(prices.values()))["price_list_id"],
        "price_list_version_id": "MULTIPLE" if len({item["price_list_version_id"] for item in prices.values()}) > 1 else next(iter(prices.values()))["price_list_version_id"],
        "price_list_version_number": "MULTIPLE" if len({item["version_number"] for item in prices.values()}) > 1 else next(iter(prices.values()))["version_number"],
    }
