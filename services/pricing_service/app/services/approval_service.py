from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import HTTPException, status
from typing import Optional, List, Dict, Any
import uuid

from app.models.pricing import PriceList, PriceListVersion, PriceListDetail, ServiceItem
from app.schemas.approval import ApprovalActionRequest, ApprovalResponse


class ApprovalService:

    @staticmethod
    def get_approval_stats(db: Session) -> Dict[str, int]:
        """Thống kê chính xác số lượng cho 5 Stat Cards"""
        price_lists = db.query(PriceList).filter(PriceList.is_deleted == False).all()

        total = len(price_lists)
        submitted = 0
        approved = 0
        effective = 0
        rejected = 0

        for pl in price_lists:
            status_val = getattr(pl, "status", None)

            if not status_val and hasattr(pl, "versions") and pl.versions:
                sorted_versions = sorted(
                    pl.versions,
                    key=lambda v: getattr(v, "version_number", 0) or 0,
                    reverse=True
                )
                if sorted_versions:
                    status_val = getattr(sorted_versions[0], "status", None)

            st = str(status_val or "").strip().upper()

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
    def _extract_services_from_pricelist(db: Session, price_list: PriceList) -> List[dict]:
        """Trích xuất danh sách dịch vụ an toàn"""
        latest_version = None
        if hasattr(price_list, "versions") and price_list.versions:
            sorted_versions = sorted(
                price_list.versions, 
                key=lambda v: getattr(v, "version_number", 0) or 0, 
                reverse=True
            )
            latest_version = sorted_versions[0] if sorted_versions else None

        query = db.query(PriceListDetail)
        if latest_version:
            query = query.filter(PriceListDetail.price_list_version_id == latest_version.id)
        else:
            query = query.filter(PriceListDetail.price_list_id == price_list.id)

        details = query.all()

        services_data = []
        for d in details:
            srv = getattr(d, "service_item", None)
            
            code = getattr(srv, "service_code", None) or getattr(d, "service_code", "SRV-DEFAULT")
            name = getattr(srv, "service_name", None) or getattr(d, "service_name", "Dịch vụ chuẩn")
            unit = getattr(srv, "unit", None) or getattr(d, "unit", "Lượt")
            price = float(d.unit_price) if getattr(d, "unit_price", None) is not None else 0.0

            services_data.append({
                "service_code": code,
                "service_name": name,
                "unit": unit,
                "price": price
            })

        return services_data

    @staticmethod
    def _build_approval_response(db: Session, price_list: PriceList, message: str) -> ApprovalResponse:
        """Mapping dữ liệu PriceList sang DTO Chuẩn cho FE"""
        price_code = price_list.price_list_code or str(price_list.id)

        latest_version = None
        if hasattr(price_list, "versions") and price_list.versions:
            sorted_versions = sorted(
                price_list.versions, 
                key=lambda v: getattr(v, "version_number", 0) or 0, 
                reverse=True
            )
            latest_version = sorted_versions[0] if sorted_versions else None

        valid_from = getattr(price_list, "valid_from", None) or (getattr(latest_version, "valid_from", None) if latest_version else None)
        valid_to = getattr(price_list, "valid_to", None) or (getattr(latest_version, "valid_to", None) if latest_version else None)

        valid_from_str = valid_from.strftime("%Y-%m-%d") if valid_from else None
        valid_to_str = valid_to.strftime("%Y-%m-%d") if valid_to else None

        updated_at_val = getattr(price_list, "updated_at", None) or getattr(price_list, "created_at", None)
        updated_at_str = updated_at_val.strftime("%Y-%m-%d %H:%M") if updated_at_val else None

        status_val = (
            getattr(price_list, "status", None) 
            or (getattr(latest_version, "status", None) if latest_version else "DRAFT")
        )
        stage_val = (
            getattr(price_list, "approval_stage", None) 
            or (getattr(latest_version, "approval_stage", None) if latest_version else "DRAFT")
        )

        ver_num = getattr(latest_version, "version_number", 1) if latest_version else 1
        version_str = f"v{ver_num}.0" if isinstance(ver_num, int) else str(ver_num)

        services = ApprovalService._extract_services_from_pricelist(db, price_list)

        return ApprovalResponse(
            price_list_id=price_code,
            price_name=price_list.price_list_name,
            target_type=getattr(price_list, "scope_type", "GENERAL"),
            specific_target=str(getattr(price_list, "scope_id", "")) if getattr(price_list, "scope_id", None) else None,
            version=version_str,
            effective_from=valid_from_str,
            effective_to=valid_to_str,
            status=str(status_val).strip().upper(),
            approval_stage=str(stage_val).strip().upper(),
            updated_by=str(getattr(price_list, "created_by", "Admin")),
            updated_at=updated_at_str,
            message=message,
            services=services
        )

    @staticmethod
    def get_approval_list(db: Session, status: Optional[str] = None) -> List[ApprovalResponse]:
        """Lấy danh sách bảng giá đơn giản"""
        price_lists = (
            db.query(PriceList)
            .filter(PriceList.is_deleted == False)
            .order_by(PriceList.created_at.desc())
            .all()
        )

        results = []
        for pl in price_lists:
            res = ApprovalService._build_approval_response(db=db, price_list=pl, message="Lấy thông tin thành công")
            
            if status and status.strip() and status != "Tất cả":
                if res.status.upper() == status.strip().upper():
                    results.append(res)
            else:
                results.append(res)

        return results

    @staticmethod
    def _find_price_list(db: Session, price_code: str) -> Optional[PriceList]:
        """Hàm dùng chung để tìm PriceList theo Code hoặc ID an toàn 100%"""
        is_valid_uuid = False
        try:
            uuid.UUID(price_code)
            is_valid_uuid = True
        except ValueError:
            is_valid_uuid = False

        conditions = [PriceList.price_list_code == price_code]
        if is_valid_uuid:
            conditions.append(PriceList.id == price_code)

        return db.query(PriceList).filter(
            PriceList.is_deleted == False,
            or_(*conditions)
        ).first()

    @staticmethod
    def submit_for_approval(db: Session, price_code: str, user_id: Optional[str] = None) -> ApprovalResponse:
        pl = ApprovalService._find_price_list(db, price_code)

        if not pl:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy bảng giá '{price_code}'")

        if hasattr(pl, "status"):
            pl.status = "SUBMITTED"
        if hasattr(pl, "approval_stage"):
            pl.approval_stage = "MANAGER_PENDING"

        if hasattr(pl, "versions") and pl.versions:
            for v in pl.versions:
                v.status = "SUBMITTED"
                if hasattr(v, "approval_stage"):
                    v.approval_stage = "MANAGER_PENDING"

        db.commit()
        db.refresh(pl)

        return ApprovalService._build_approval_response(db=db, price_list=pl, message="Đã gửi phê duyệt bảng giá thành công.")

    @staticmethod
    def manager_approve(
        db: Session, price_code: str, payload: ApprovalActionRequest, manager_id: Optional[str] = None
    ) -> ApprovalResponse:
        act = payload.action.upper()
        if act not in ["APPROVE", "REJECT"]:
            raise HTTPException(status_code=400, detail="Hành động không hợp lệ.")

        pl = ApprovalService._find_price_list(db, price_code)

        if not pl:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy bảng giá '{price_code}'")

        target_status = "APPROVED" if act == "APPROVE" else "REJECTED"
        target_stage = "APPROVED" if act == "APPROVE" else "REJECTED"
        reason_text = payload.rejected_reason or payload.comment or ""

        approved_by_uuid = None
        if manager_id:
            try:
                approved_by_uuid = uuid.UUID(manager_id)
            except ValueError:
                approved_by_uuid = None

        if hasattr(pl, "status"):
            pl.status = target_status
        if hasattr(pl, "approval_stage"):
            pl.approval_stage = target_stage

        if hasattr(pl, "versions") and pl.versions:
            for v in pl.versions:
                v.status = target_status
                if hasattr(v, "approval_stage"):
                    v.approval_stage = target_stage
                
                if act == "APPROVE":
                    if hasattr(v, "approved_by"):
                        v.approved_by = approved_by_uuid
                    if hasattr(v, "rejected_reason"):
                        v.rejected_reason = None
                else:
                    if hasattr(v, "rejected_reason"):
                        v.rejected_reason = reason_text

        db.commit()
        db.refresh(pl)

        msg = "Phê duyệt thành công." if act == "APPROVE" else f"Từ chối thành công. Lý do: {reason_text}"
        return ApprovalService._build_approval_response(db=db, price_list=pl, message=msg)