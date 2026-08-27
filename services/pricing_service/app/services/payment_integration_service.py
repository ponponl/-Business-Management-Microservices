import uuid
from datetime import date
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from app.models.pricing import PriceList, PriceListVersion, PriceListDetail, ServiceItem
from app.schemas.payment_integration import PaymentValidationRequest


class PaymentIntegrationService:

    @staticmethod
    def validate_price_list_for_payment(db: Session, payload: PaymentValidationRequest) -> Dict[str, Any]:
        # 1. Kiểm tra tồn tại bảng giá 
        conds = [PriceList.price_list_code == payload.price_table_id]
        try:
            conds.append(PriceList.id == uuid.UUID(payload.price_table_id))
        except ValueError:
            pass

        price_list = db.query(PriceList).filter(PriceList.is_deleted.is_(False), or_(*conds)).first()
        if not price_list:
            return {
                "is_valid": False,
                "price_list_id": payload.price_table_id,
                "price_list_version_id": "",
                "version_number": "",
                "message": f"Bảng giá '{payload.price_table_id}' không tồn tại trong hệ thống.",
                "items": []
            }

        # 2. Kiểm tra Scope 
        scope_type = str(price_list.scope_type or "").upper()
        scope_id = str(price_list.scope_id or "").strip()

        if scope_type == "CUSTOMER":
            if not payload.customer_id or scope_id != payload.customer_id.strip():
                return {
                    "is_valid": False,
                    "price_list_id": str(price_list.id),
                    "price_list_version_id": "",
                    "version_number": "",
                    "message": f"Bảng giá chỉ áp dụng cho khách hàng '{scope_id}', không khớp với '{payload.customer_id}'.",
                    "items": []
                }
        elif scope_type == "CONTRACT":
            if not payload.contract_id or scope_id != payload.contract_id.strip():
                return {
                    "is_valid": False,
                    "price_list_id": str(price_list.id),
                    "price_list_version_id": "",
                    "version_number": "",
                    "message": f"Bảng giá chỉ áp dụng cho hợp đồng '{scope_id}', không khớp với '{payload.contract_id}'.",
                    "items": []
                }

        # 3. Lấy phiên bản đang EFFECTIVE và kiểm tra khoảng thời gian
        version = db.query(PriceListVersion).filter(
            PriceListVersion.price_list_id == price_list.id,
            PriceListVersion.status == "EFFECTIVE"
        ).order_by(PriceListVersion.created_at.desc()).first()

        if not version:
            return {
                "is_valid": False,
                "price_list_id": str(price_list.id),
                "price_list_version_id": "",
                "version_number": "",
                "message": f"Bảng giá '{price_list.price_list_name}' hiện không có phiên bản nào ở trạng thái EFFECTIVE.",
                "items": []
            }

        # 4. Kiểm tra thời gian hiệu lực 
        if version.valid_from > payload.period_start:
            return {
                "is_valid": False,
                "price_list_id": str(price_list.id),
                "price_list_version_id": str(version.id),
                "version_number": version.version_number,
                "message": f"Bảng giá chưa có hiệu lực tại ngày bắt đầu kỳ thanh toán ({version.valid_from} > {payload.period_start}).",
                "items": []
            }

        if version.valid_to is not None and version.valid_to < payload.period_end:
            return {
                "is_valid": False,
                "price_list_id": str(price_list.id),
                "price_list_version_id": str(version.id),
                "version_number": version.version_number,
                "message": f"Bảng giá đã hết hạn trước khi kết thúc kỳ thanh toán ({version.valid_to} < {payload.period_end}).",
                "items": []
            }

        # 5. Lấy danh sách chi tiết các dịch vụ và đơn giá 
        details = db.query(PriceListDetail, ServiceItem).join(
            ServiceItem, ServiceItem.id == PriceListDetail.service_item_id
        ).filter(
            PriceListDetail.price_list_version_id == version.id
        ).all()

        items = [
            {
                "service_item_id": str(srv.id),
                "service_code": srv.service_code,
                "service_name": srv.service_name,
                "unit": srv.unit or "",
                "unit_price": float(dt.unit_price)
            }
            for dt, srv in details
        ]

        return {
            "is_valid": True,
            "price_list_id": str(price_list.id),
            "price_list_version_id": str(version.id),
            "version_number": version.version_number,
            "message": "Bảng giá hợp lệ để lập bảng thanh toán.",
            "items": items
        }