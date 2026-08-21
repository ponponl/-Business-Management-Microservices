import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy import or_, desc, func
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
    def _validate_overlapping_time(
        db: Session,
        scope_type: str,
        scope_id: Optional[str],
        effective_from: Optional[datetime],
        effective_to: Optional[datetime],
        exclude_price_list_id: Optional[Any] = None,
    ):
        """
        Kiểm tra va chạm thời gian hiệu lực giữa các bảng giá cùng scope_type và scope_id.
        Xử lý chuẩn xác cả trường hợp scope_id là None/Rỗng.
        """
        if not effective_from:
            return

        target_scope_id = scope_id.strip() if scope_id and str(scope_id).strip() != "" else None

        query = (
            db.query(PriceListVersion)
            .join(PriceList, PriceList.id == PriceListVersion.price_list_id)
            .filter(
                PriceList.scope_type == scope_type,
                PriceListVersion.status.in_(["SUBMITTED", "APPROVED", "EFFECTIVE"]),
            )
        )

        if target_scope_id is None:
            query = query.filter(or_(PriceList.scope_id.is_(None), PriceList.scope_id == ""))
        else:
            query = query.filter(PriceList.scope_id == target_scope_id)

        if exclude_price_list_id:
            query = query.filter(PriceList.id != exclude_price_list_id)

        existing_versions = query.all()

        for ver in existing_versions:
            v_from = ver.valid_from
            v_to = ver.valid_to

            start_overlap = (v_to is None) or (effective_from <= v_to)
            end_overlap = (effective_to is None) or (v_from is None) or (effective_to >= v_from)

            if start_overlap and end_overlap:
                from_str = v_from.strftime("%d/%m/%Y") if v_from else "Không giới hạn"
                to_str = v_to.strftime("%d/%m/%Y") if v_to else "Không giới hạn"
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Thời gian hiệu lực bị chồng lấp với bảng giá khác cùng đối tượng! "
                        f"Bảng giá hiện tại đang có hiệu lực từ {from_str} đến {to_str}."
                    ),
                )

    @staticmethod
    def _generate_next_price_code(db: Session) -> str:
        """
        Tìm mã bảng giá có 3 số cuối lớn nhất trong năm hiện tại và cộng thêm 1.
        Ví dụ: Lớn nhất là PL-2026-215 -> Tạo mã mới là PL-2026-216.
        """
        year = datetime.now().year
        prefix = f"PL-{year}-"

        codes = (
            db.query(PriceList.price_list_code)
            .filter(PriceList.price_list_code.like(f"{prefix}%"))
            .all()
        )

        max_number = 0
        pattern = re.compile(rf"^{prefix}(\d+)$")

        for (code_val,) in codes:
            if code_val:
                match = pattern.match(code_val.strip())
                if match:
                    num = int(match.group(1))
                    if num > max_number:
                        max_number = num

        next_number = max_number + 1
        return f"{prefix}{next_number:03d}"

    @staticmethod
    def get_stats(db: Session) -> Dict[str, int]:
        """Tính toán số liệu giữ nguyên 5 Stat Cards ở UI"""
        
        subquery = (
            db.query(
                PriceListVersion.price_list_id,
                func.max(PriceListVersion.version_number).label("max_ver")
            )
            .group_by(PriceListVersion.price_list_id)
            .subquery()
        )

        latest_versions = (
            db.query(PriceListVersion)
            .join(
                subquery,
                (PriceListVersion.price_list_id == subquery.c.price_list_id) &
                (PriceListVersion.version_number == subquery.c.max_ver)
            )
            .all()
        )

        total = db.query(PriceList).count()
        submitted = 0
        approved = 0
        effective = 0
        rejected = 0

        for ver in latest_versions:
            st = str(ver.status or "").strip().upper()
            if st == "SUBMITTED":
                submitted += 1
            elif st == "APPROVED":
                approved += 1
            elif st == "EFFECTIVE":
                effective += 1
            elif st == "REJECTED":
                rejected += 1

        return {
            "total": total,
            "submitted": submitted,
            "approved": approved,
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
        """Xử lý lọc, tìm kiếm và phân trang danh sách bảng giá (Bổ sung lọc SUPERSEDED, EXPIRED)"""

        query = db.query(PriceList, PriceListVersion).join(
            PriceListVersion, PriceList.id == PriceListVersion.price_list_id
        )

        # Lọc trạng thái (Chấp nhận cả SUPERSEDED và EXPIRED từ UI)
        if status and status != "Tất cả":
            query = query.filter(PriceListVersion.status.ilike(status.strip()))

        if apply_type and apply_type != "Tất cả":
            query = query.filter(PriceList.scope_type.ilike(apply_type.strip()))

        if customer and customer != "Tất cả":
            query = query.filter(PriceList.price_list_name.ilike(f"%{customer.strip()}%"))

        if search and search.strip():
            search_term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    PriceList.price_list_code.ilike(search_term),
                    PriceList.price_list_name.ilike(search_term),
                )
            )

        total_count = query.count()

        offset = (page - 1) * page_size
        records = query.order_by(
            desc(PriceListVersion.version_number), 
            desc(PriceList.created_at)
        ).offset(offset).limit(page_size).all()

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

            created_at_val = getattr(pl, "created_at", None)
            created_at_str = created_at_val.strftime("%d/%m/%Y %H:%M") if created_at_val else "N/A"

            reason = (
                getattr(ver, "rejected_reason", None)
                or getattr(ver, "rejection_reason", None)
                or getattr(ver, "reject_reason", None)
                or getattr(ver, "rejection_note", None)
                or ""
            )

            items.append(
                {
                    "id": pl.price_list_code or str(pl.id),
                    "name": pl.price_list_name or "N/A",
                    "contractId": str(
                        getattr(pl, "contract_id", None) or getattr(pl, "scope_id", None) or "N/A"
                    ),
                    "type": str(pl.scope_type or "GENERAL").upper(),
                    "version": version_str,
                    "effectiveTime": effective_time,
                    "status": str(ver.status or "DRAFT").upper(),
                    "rejectReason": reason,
                    "rejectionReason": reason,
                    "updatedBy": str(getattr(pl, "created_by", None) or "Hệ thống"),
                    "updatedAt": created_at_str,
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
            .order_by(
                desc(PriceListVersion.status == 'REJECTED'),
                desc(PriceListVersion.version_number),
                desc(PriceListVersion.id)
            )
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

        reason = (
            getattr(ver, "rejected_reason", None)
            or getattr(ver, "rejection_reason", None)
            or getattr(ver, "reject_reason", None)
            or getattr(ver, "rejection_note", None)
            or getattr(pl, "rejected_reason", None)
            or getattr(pl, "rejection_reason", None)
            or ""
        )

        return {
            "id": pl.price_list_code or str(pl.id),
            "priceCode": pl.price_list_code or "N/A",
            "priceName": pl.price_list_name or "N/A",
            "scopeType": str(pl.scope_type or "CUSTOMER"),
            "scopeId": str(
                getattr(pl, "scope_id", None) or getattr(pl, "contract_id", None) or getattr(pl, "customer_id", None) or "N/A"
            ),
            "version": version_str,
            "status": str(ver.status or "DRAFT").upper(),
            "rejectReason": reason,
            "rejectionReason": reason,
            "validFrom": valid_from_str,
            "validTo": valid_to_str,
            "services": services_data,
        }

    @staticmethod
    def create_price_list(
        db: Session, payload: PriceListCreate
    ) -> Dict[str, Any]:
        """Tạo mới bảng giá"""
        try:
            PriceListService._validate_overlapping_time(
                db=db,
                scope_type=payload.target_type,
                scope_id=payload.specific_target,
                effective_from=payload.effective_from,
                effective_to=payload.effective_to,
            )

            price_code = payload.price_code
            if not price_code:
                price_code = PriceListService._generate_next_price_code(db)

            new_price_list = PriceList(
                price_list_code=price_code,
                price_list_name=payload.price_name,
                scope_type=payload.target_type,
                scope_id=payload.specific_target,
            )
            db.add(new_price_list)
            db.flush()

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

        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Lỗi tạo bảng giá: {str(e)}",
            )

    @staticmethod
    def update_price_list(
        db: Session, price_code: str, payload: PriceListCreate
    ) -> Dict[str, Any]:
        """Cập nhật thông tin Bảng giá"""
        
        filter_conditions = [PriceList.price_list_code == price_code]
        try:
            uuid_obj = uuid.UUID(price_code)
            filter_conditions.append(PriceList.id == uuid_obj)
        except ValueError:
            pass  

        record = (
            db.query(PriceList, PriceListVersion)
            .join(PriceListVersion, PriceList.id == PriceListVersion.price_list_id)
            .filter(or_(*filter_conditions))
            .order_by(desc(PriceListVersion.version_number))
            .first()
        )

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy bảng giá '{price_code}'"
            )

        pl, ver = record
        current_status = str(ver.status or "").upper()

        if current_status not in ["DRAFT", "REJECTED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Không thể chỉnh sửa bảng giá ở trạng thái '{current_status}'. Chỉ cho phép sửa khi DRAFT hoặc REJECTED."
            )

        PriceListService._validate_overlapping_time(
            db=db,
            scope_type=payload.target_type,
            scope_id=payload.specific_target,
            effective_from=payload.effective_from,
            effective_to=payload.effective_to,
            exclude_price_list_id=pl.id,
        )

        try:
            pl.price_list_name = payload.price_name
            pl.scope_type = payload.target_type
            pl.scope_id = payload.specific_target

            ver.valid_from = payload.effective_from
            ver.valid_to = payload.effective_to
            
            if payload.status:
                ver.status = payload.status.upper()

            for field in ["rejected_reason", "rejection_reason", "reject_reason", "rejection_note"]:
                if hasattr(ver, field):
                    setattr(ver, field, None)

            db.query(PriceListDetail).filter(
                PriceListDetail.price_list_version_id == ver.id
            ).delete(synchronize_session=False)

            for item in payload.services:
                if not item.service_code:
                    continue  

                service_item = (
                    db.query(ServiceItem)
                    .filter(ServiceItem.service_code == item.service_code)
                    .first()
                )

                if service_item:
                    service_item.service_name = item.service_name
                    service_item.unit = item.unit
                else:
                    service_item = ServiceItem(
                        service_code=item.service_code,
                        service_name=item.service_name,
                        unit=item.unit,
                        status="ACTIVE"
                    )
                    db.add(service_item)
                    db.flush()  

                detail = PriceListDetail(
                    price_list_id=pl.id,
                    price_list_version_id=ver.id,
                    service_item_id=service_item.id,
                    unit_price=item.price,
                )
                db.add(detail)

            db.commit()
            return {
                "id": pl.price_list_code,
                "message": "Cập nhật bảng giá thành công"
            }

        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Lỗi khi cập nhật bảng giá: {str(e)}"
            )