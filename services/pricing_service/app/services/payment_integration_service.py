import uuid
from datetime import date
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from app.models.pricing import PriceList, PriceListVersion, PriceListDetail, ServiceItem
from app.schemas.payment_integration import PaymentPriceResolveRequest, PaymentValidationRequest


class PaymentIntegrationService:

    @staticmethod
    def resolve_prices_for_payment(db: Session, payload: PaymentPriceResolveRequest) -> Dict[str, Any]:
        scope_id = lambda value: str(value or "").strip()
        candidates = db.query(PriceList).filter(
            PriceList.is_deleted.is_(False),
            PriceList.scope_type.in_(["GENERAL", "CUSTOMER", "CONTRACT"]),
        ).all()
        priority = {"CONTRACT": 0, "CUSTOMER": 1, "GENERAL": 2}
        resolved = []
        for operation_date in sorted(set(payload.operation_dates)):
            matching_lists = []
            for price_list in candidates:
                list_type = str(price_list.scope_type or "").upper()
                list_scope = scope_id(price_list.scope_id)
                if list_type == "CUSTOMER" and list_scope != scope_id(payload.customer_id):
                    continue
                if list_type == "CONTRACT" and list_scope != scope_id(payload.contract_id):
                    continue
                version = db.query(PriceListVersion).filter(
                    PriceListVersion.price_list_id == price_list.id,
                    func.upper(PriceListVersion.status) == "EFFECTIVE",
                    PriceListVersion.valid_from <= operation_date,
                    (PriceListVersion.valid_to.is_(None) | (PriceListVersion.valid_to >= operation_date)),
                ).order_by(PriceListVersion.created_at.desc()).first()
                if version:
                    matching_lists.append((priority.get(list_type, 99), price_list, version))
            if not matching_lists:
                raise HTTPException(422, f"Không tìm thấy bảng giá hiệu lực cho ngày vận hành {operation_date}")
            _, price_list, version = sorted(matching_lists, key=lambda item: item[0])[0]
            details = db.query(PriceListDetail, ServiceItem).join(
                ServiceItem, ServiceItem.id == PriceListDetail.service_item_id
            ).filter(PriceListDetail.price_list_version_id == version.id).all()
            detail_by_code = {srv.service_code: (detail, srv) for detail, srv in details}
            for service_code in sorted(set(payload.service_codes)):
                detail, service = detail_by_code.get(service_code, (None, None))
                if not detail:
                    continue
                resolved.append({
                    "operation_date": operation_date,
                    "service_item_id": str(service.id),
                    "service_code": service.service_code,
                    "service_name": service.service_name,
                    "unit": service.unit or "",
                    "unit_price": float(detail.unit_price),
                    "price_list_id": str(price_list.id),
                    "price_list_version_id": str(version.id),
                    "version_number": version.version_number,
                    "price_list_name": getattr(version, "price_list_name", None) or price_list.price_list_name,
                })
        return {"is_valid": True, "message": "Đã tự động xác định bảng giá theo ngày vận hành.", "items": resolved}

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

        # A single payment board cannot combine prices from multiple effective
        # versions. Reject a period that overlaps a higher-priority price list.
        scope_priority = {"GENERAL": 0, "CUSTOMER": 1, "CONTRACT": 2}
        selected_priority = scope_priority.get(scope_type, -1)
        applicable_lists = db.query(PriceList).filter(
            PriceList.is_deleted.is_(False),
            PriceList.scope_type.in_(["GENERAL", "CUSTOMER", "CONTRACT"]),
        ).all()
        for applicable_list in applicable_lists:
            candidate_type = str(applicable_list.scope_type or "").upper()
            candidate_scope_id = str(applicable_list.scope_id or "").strip()
            matches_scope = (
                candidate_type == "GENERAL"
                or (candidate_type == "CUSTOMER" and candidate_scope_id == str(payload.customer_id or "").strip())
                or (candidate_type == "CONTRACT" and candidate_scope_id == str(payload.contract_id or "").strip())
            )
            if applicable_list.id == price_list.id or not matches_scope:
                continue
            if scope_priority.get(candidate_type, -1) <= selected_priority:
                continue
            overlapping_version = db.query(PriceListVersion).filter(
                PriceListVersion.price_list_id == applicable_list.id,
                func.upper(PriceListVersion.status) == "EFFECTIVE",
                PriceListVersion.valid_from <= payload.period_end,
                (PriceListVersion.valid_to.is_(None) | (PriceListVersion.valid_to >= payload.period_start)),
            ).first()
            if overlapping_version:
                return {
                    "is_valid": False,
                    "price_list_id": str(price_list.id),
                    "price_list_version_id": "",
                    "version_number": "",
                    "message": (
                        f"Kỳ thanh toán giao nhau với bảng giá ưu tiên '{applicable_list.price_list_name}' "
                        f"từ ngày {overlapping_version.valid_from}. Hãy tách kỳ theo từng bảng giá."
                    ),
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