import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.pricing import (
    PriceList,
    PriceListDetail,
    PriceListVersion,
    ServiceItem,
)
from app.schemas.price_list import PriceListCreate


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
            st = str(ver.status or "").upper()
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
            "rejected": rejected,
        }

    @staticmethod
    def get_paginated_list(
        db: Session,
        status: Optional[str] = None,
        apply_type: Optional[str] = None,
        customer: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
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
                    PriceList.price_list_name.ilike(search_term),
                )
            )

        total_count = query.count()

        offset = (page - 1) * page_size
        records = query.offset(offset).limit(page_size).all()

        items: List[Dict[str, Any]] = []
        for pl, ver in records:
            valid_from = getattr(ver, "valid_from", None)
            valid_to = getattr(ver, "valid_to", None)

            start_str = valid_from.strftime("%d/%m/%Y") if valid_from else ""
            end_str = valid_to.strftime("%d/%m/%Y") if valid_to else ""

            if start_str and end_str:
                effective_time = f"{start_str} - {end_str}"
            elif start_str:
                effective_time = f"Từ {start_str}"
            else:
                effective_time = "N/A"

            ver_num = getattr(ver, "version_number", 1)
            version_str = (
                f"v{ver_num}.0" if isinstance(ver_num, int) else str(ver_num)
            )

            items.append(
                {
                    "id": pl.price_list_code or "N/A",
                    "name": pl.price_list_name or "N/A",
                    "contractId": str(
                        getattr(pl, "contract_id", None) or "N/A"
                    ),
                    "type": str(pl.scope_type or "GENERAL").upper(),
                    "version": version_str,
                    "effectiveTime": effective_time,
                    "status": str(ver.status or "DRAFT").upper(),
                    "updatedBy": "Hệ thống",
                    "updatedAt": start_str or "01/01/2026 00:00",
                }
            )

        customers_db = (
            db.query(PriceList.price_list_name)
            .filter(PriceList.price_list_name.isnot(None))
            .distinct()
            .all()
        )
        customer_list = ["Tất cả"] + [c[0] for c in customers_db if c[0]]

        type_list = [
            "Tất cả",
            "CUSTOMER",
            "CONTRACT",
            "GENERAL",
            "SERVICE_GROUP",
            "SERVICE_TYPE",
        ]

        return {
            "items": items,
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "available_types": type_list,
            "available_customers": customer_list,
        }

    @staticmethod
    def get_detail_by_code(db: Session, price_code: str) -> Dict[str, Any]:
        """Lấy thông tin chi tiết Bảng giá"""

        is_valid_uuid = False
        try:
            uuid.UUID(price_code)
            is_valid_uuid = True
        except ValueError:
            is_valid_uuid = False

        conditions = [PriceList.price_list_code == price_code]
        if is_valid_uuid:
            conditions.append(PriceList.id == price_code)

        record = (
            db.query(PriceList, PriceListVersion)
            .join(
                PriceListVersion,
                PriceList.id == PriceListVersion.price_list_id,
            )
            .filter(or_(*conditions))
            .first()
        )

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy bảng giá có mã '{price_code}'",
            )

        pl, ver = record

        valid_from = getattr(ver, "valid_from", None)
        valid_to = getattr(ver, "valid_to", None)

        valid_from_str = (
            valid_from.strftime("%Y-%m-%d") if valid_from else ""
        )
        valid_to_str = valid_to.strftime("%Y-%m-%d") if valid_to else ""

        ver_num = getattr(ver, "version_number", 1)
        version_str = (
            f"{ver_num}.0" if isinstance(ver_num, int) else str(ver_num)
        )

        services_data = []
        details = (
            db.query(PriceListDetail)
            .filter(PriceListDetail.price_list_version_id == ver.id)
            .all()
        )

        for item in details:
            srv = item.service_item
            services_data.append(
                {
                    "code": srv.service_code if srv else "SRV-DEFAULT",
                    "name": srv.service_name if srv else "Dịch vụ định mức",
                    "unit": srv.unit if srv else "Lượt",
                    "price": float(item.unit_price or 0.0),
                }
            )

        return {
            "id": pl.price_list_code or str(pl.id),
            "priceCode": pl.price_list_code or "N/A",
            "priceName": pl.price_list_name or "N/A",
            "scopeType": str(pl.scope_type or "CUSTOMER"),
            "scopeId": str(
                pl.scope_id or pl.contract_id or pl.customer_id or "N/A"
            ),
            "version": version_str,
            "status": str(ver.status or "DRAFT").upper(),
            "validFrom": valid_from_str,
            "validTo": valid_to_str,
            "services": services_data,
        }

    @staticmethod
    def create_price_list(
        db: Session, payload: PriceListCreate
    ) -> Dict[str, Any]:
        """Tạo mới bảng giá, phiên bản và chi tiết các dịch vụ từ Pydantic Schema"""
        try:
            price_code = payload.price_code
            if not price_code:
                year = datetime.now().year
                count = db.query(PriceList).count() + 1
                price_code = f"PL-{year}-{count:03d}"

            # 2. Tạo record PriceList (Bảng chính)
            new_price_list = PriceList(
                price_list_code=price_code,
                price_list_name=payload.price_name,
                scope_type=payload.target_type,
                scope_id=payload.specific_target,
            )
            db.add(new_price_list)
            db.flush()

            # 3. Tạo record PriceListVersion
            new_version = PriceListVersion(
                price_list_id=new_price_list.id,
                version_number=1,
                status=payload.status.upper() if payload.status else "DRAFT",
                valid_from=payload.effective_from,
                valid_to=payload.effective_to,
            )
            db.add(new_version)
            db.flush()

            for item in payload.services:
                service_item = (
                    db.query(ServiceItem)
                    .filter(ServiceItem.service_code == item.service_code)
                    .first()
                )

                if not service_item and item.service_code:
                    service_item = ServiceItem(
                        service_code=item.service_code,
                        service_name=item.service_name,
                        unit=item.unit,
                    )
                    db.add(service_item)
                    db.flush()

                detail = PriceListDetail(
                    price_list_id=new_price_list.id,
                    price_list_version_id=new_version.id,
                    service_item_id=(
                        service_item.id if service_item else None
                    ),
                    unit_price=item.price,
                )
                db.add(detail)

            db.commit()
            return {
                "id": new_price_list.price_list_code,
                "message": "Tạo mới bảng giá thành công",
            }

        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Lỗi tạo bảng giá: {str(e)}",
            )