from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, Dict, Any, List
from app.models.pricing import PriceList, PriceListVersion


class PriceListService:

    @staticmethod
    def get_stats(db: Session) -> Dict[str, int]:
        """Tính toán số liệu cho 4 Stat Cards từ PriceListVersion"""
        versions = db.query(PriceListVersion).all()
        
        total = db.query(PriceList).count()
        submitted = 0
        effective = 0
        rejected = 0

        for ver in versions:
            st = str(ver.status or '').upper()
            if st == "SUBMITTED":
                submitted += 1
            elif st == "EFFECTIVE":
                effective += 1
            elif st == "REJECTED":
                rejected += 1

        return {
            "total": total,
            "submitted": submitted,
            "effective": effective,
            "rejected": rejected
        }

    @staticmethod
    def get_paginated_list(
        db: Session,
        status: Optional[str] = None,
        apply_type: Optional[str] = None,
        customer: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 10
    ) -> Dict[str, Any]:
        """Xử lý lọc, tìm kiếm và phân trang danh sách bảng giá"""
        
        query = db.query(PriceList, PriceListVersion).join(
            PriceListVersion, PriceList.id == PriceListVersion.price_list_id
        )

        if status and status != "Tất cả":
            query = query.filter(PriceListVersion.status == status)

        if apply_type and apply_type != "Tất cả":
            query = query.filter(PriceList.scope_type == apply_type)

        if customer and customer != "Tất cả":
            query = query.filter(PriceList.price_list_name == customer)

        if search:
            search_term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    PriceList.price_list_code.ilike(search_term),
                    PriceList.price_list_name.ilike(search_term)
                )
            )

        total_count = query.count()

        offset = (page - 1) * page_size
        records = query.offset(offset).limit(page_size).all()

        items: List[Dict[str, Any]] = []
        for pl, ver in records:
            # Xử lý format Ngày hiệu lực an toàn
            valid_from = getattr(ver, 'valid_from', None)
            valid_to = getattr(ver, 'valid_to', None)
            
            start_str = valid_from.strftime("%d/%m/%Y") if valid_from else ""
            end_str = valid_to.strftime("%d/%m/%Y") if valid_to else ""
            
            if start_str and end_str:
                effective_time = f"{start_str} - {end_str}"
            elif start_str:
                effective_time = f"Từ {start_str}"
            else:
                effective_time = "N/A"

            ver_num = getattr(ver, 'version_number', 1)
            version_str = f"v{ver_num}.0" if isinstance(ver_num, int) else str(ver_num)

            items.append({
                "id": pl.price_list_code or "N/A",
                "name": pl.price_list_name or "N/A",
                "contractId": str(getattr(pl, 'contract_id', None) or "N/A"),
                "type": str(pl.scope_type or "GENERAL").upper(),
                "version": version_str,
                "effectiveTime": effective_time,
                "status": str(ver.status or "DRAFT").upper(),
                "updatedBy": "Hệ thống",
                "updatedAt": start_str or "01/01/2026 00:00"
            })

        customers_db = db.query(PriceList.price_list_name).filter(PriceList.price_list_name.isnot(None)).distinct().all()
        customer_list = ["Tất cả"] + [c[0] for c in customers_db if c[0]]

        type_list = ['Tất cả', 'CUSTOMER', 'CONTRACT', 'GENERAL', 'SERVICE_GROUP', 'SERVICE_TYPE']

        return {
            "items": items,
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "available_types": type_list,
            "available_customers": customer_list
        }