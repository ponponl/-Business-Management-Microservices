import uuid
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from fastapi import HTTPException, status

from app.models.pricing import PriceList, PriceListVersion, PriceListDetail, ServiceItem
from app.schemas.approval import ApprovalActionRequest, ApprovalResponse


class ApprovalService:

    @staticmethod
    def _get_latest_version(price_list: PriceList) -> Optional[PriceListVersion]:
        """Hàm phụ trợ lấy Version mới nhất theo version_number"""
        if not price_list or not price_list.versions:
            return None
        return max(
            price_list.versions,
            key=lambda v: getattr(v, "version_number", 0) or 0
        )

    @staticmethod
    def get_approval_stats(db: Session) -> Dict[str, int]:
        """Thống kê 5 chỉ số chính cho Stat Cards dựa trên Version mới nhất"""
        price_lists = (
            db.query(PriceList)
            .options(joinedload(PriceList.versions))
            .filter(or_(PriceList.is_deleted == False, PriceList.is_deleted == None))
            .all()
        )

        total = len(price_lists)
        submitted = approved = effective = rejected = 0

        for pl in price_lists:
            latest_v = ApprovalService._get_latest_version(pl)
            
            st_raw = getattr(latest_v, "status", "DRAFT") if latest_v else "DRAFT"
            st = str(st_raw.value if hasattr(st_raw, "value") else st_raw).strip().upper()

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
        """Trích xuất danh sách dịch vụ an toàn (Bổ sung đa dạng key-naming cho Frontend)"""
        latest_version = ApprovalService._get_latest_version(price_list)

        query = db.query(PriceListDetail).options(joinedload(PriceListDetail.service_item))
        if latest_version:
            query = query.filter(PriceListDetail.price_list_version_id == latest_version.id)
        else:
            query = query.filter(PriceListDetail.price_list_id == price_list.id)

        details = query.all()

        services_data = []
        for d in details:
            srv = d.service_item
            
            # 1. Lấy service_code: Ưu tiên srv -> d.service_code -> d.service_id
            code = (
                getattr(srv, "service_code", None) or 
                getattr(srv, "code", None) or 
                getattr(d, "service_code", None) or 
                (str(d.service_id) if getattr(d, "service_id", None) else None) or 
                "-"
            )
            
            # 2. Lấy service_name: Ưu tiên srv -> d.service_name -> d.description
            name = (
                getattr(srv, "service_name", None) or 
                getattr(srv, "name", None) or 
                getattr(d, "service_name", None) or 
                getattr(d, "description", None) or 
                "Dịch vụ chuẩn"
            )
            
            # 3. Lấy unit: Ưu tiên d.unit -> srv.unit
            unit = (
                getattr(d, "unit", None) or 
                getattr(srv, "unit", None) or 
                "Lượt"
            )
            
            # 4. Lấy price
            price = float(d.unit_price) if getattr(d, "unit_price", None) is not None else 0.0

            # Bổ sung đầy đủ biến thể key naming cho Frontend React/Vue/AntD
            services_data.append({
                # Mã dịch vụ
                "service_code": str(code),
                "serviceCode": str(code),
                "code": str(code),

                # Tên dịch vụ
                "service_name": str(name),
                "serviceName": str(name),
                "name": str(name),
                "title": str(name),

                # Đơn vị & Đơn giá
                "unit": str(unit),
                "price": price,
                "unit_price": price,
                "unitPrice": price
            })

        return services_data

    @staticmethod
    def _build_approval_response(db: Session, price_list: PriceList, message: str) -> ApprovalResponse:
        """Mapping dữ liệu PriceList sang DTO Chuẩn cho FE"""
        price_code = price_list.price_list_code or str(price_list.id)
        latest_version = ApprovalService._get_latest_version(price_list)

        valid_from_str = latest_version.valid_from.strftime("%Y-%m-%d") if (latest_version and latest_version.valid_from) else None
        valid_to_str = latest_version.valid_to.strftime("%Y-%m-%d") if (latest_version and latest_version.valid_to) else None

        updated_at_val = price_list.updated_at or price_list.created_at
        updated_at_str = updated_at_val.strftime("%Y-%m-%d %H:%M") if updated_at_val else None

        st_raw = getattr(latest_version, "status", "DRAFT") if latest_version else "DRAFT"
        status_val = str(st_raw.value if hasattr(st_raw, "value") else st_raw).strip().upper()

        stg_raw = getattr(latest_version, "approval_stage", "DRAFT") if latest_version else "DRAFT"
        stage_val = str(stg_raw.value if hasattr(stg_raw, "value") else stg_raw).strip().upper()

        # TỰ ĐỘNG CHUYỂN TRẠNG THÁI EXPIRED NẾU QUÁ HẠN VALID_TO
        today = date.today()
        if latest_version and latest_version.valid_to and latest_version.valid_to < today:
            if status_val not in ["SUPERSEDED", "DRAFT", "REJECTED"]:
                status_val = "EXPIRED"
                stage_val = "EXPIRED"

        ver_num = latest_version.version_number if latest_version else 1
        version_str = f"v{ver_num}.0"

        scope_raw = getattr(price_list, "scope_type", "GENERAL")
        target_type = str(scope_raw.value if hasattr(scope_raw, "value") else scope_raw).strip().upper() if scope_raw else "GENERAL"

        specific_target = None
        if target_type in ["CUSTOMER", "CUSTOMER_SPECIFIC"] and getattr(price_list, "customer_id", None):
            specific_target = str(price_list.customer_id)
        elif target_type in ["CONTRACT", "CONTRACT_SPECIFIC"] and getattr(price_list, "contract_id", None):
            specific_target = str(price_list.contract_id)
        else:
            specific_target = str(price_list.scope_id) if getattr(price_list, "scope_id", None) else None

        services = ApprovalService._extract_services_from_pricelist(db, price_list)

        raw_created_by = str(price_list.created_by) if getattr(price_list, "created_by", None) else "Staff"
        updated_by_str = "Staff" if len(raw_created_by) > 20 else raw_created_by

        return ApprovalResponse(
            price_list_id=price_code,
            price_name=price_list.price_list_name,
            target_type=target_type,
            specific_target=specific_target,
            version=version_str,
            effective_from=valid_from_str,
            effective_to=valid_to_str,
            status=status_val,
            approval_stage=stage_val,
            updated_by=updated_by_str,
            updated_at=updated_at_str,
            message=message,
            services=services
        )

    @staticmethod
    def get_approval_list(db: Session, status: Optional[str] = None) -> List[ApprovalResponse]:
        """Lấy danh sách bảng giá có lọc theo các trạng thái"""
        price_lists = (
            db.query(PriceList)
            .options(joinedload(PriceList.versions))
            .filter(or_(PriceList.is_deleted == False, PriceList.is_deleted == None))
            .order_by(PriceList.created_at.desc())
            .all()
        )

        results = []
        clean_status = status.strip().upper() if status and status.strip() else None

        for pl in price_lists:
            res = ApprovalService._build_approval_response(db=db, price_list=pl, message="Lấy thông tin thành công")
            
            if clean_status and clean_status not in ["TẤT CẢ", "ALL"]:
                if res.status.upper() == clean_status:
                    results.append(res)
            else:
                results.append(res)

        return results

    @staticmethod
    def _find_price_list(db: Session, price_code: str) -> Optional[PriceList]:
        """Tìm PriceList theo Code hoặc ID an toàn kèm eager load versions"""
        is_valid_uuid = False
        try:
            uuid.UUID(price_code)
            is_valid_uuid = True
        except ValueError:
            is_valid_uuid = False

        conditions = [PriceList.price_list_code == price_code]
        if is_valid_uuid:
            conditions.append(PriceList.id == price_code)

        return db.query(PriceList).options(
            joinedload(PriceList.versions)
        ).filter(
            or_(PriceList.is_deleted == False, PriceList.is_deleted == None),
            or_(*conditions)
        ).first()

    @staticmethod
    def submit_for_approval(db: Session, price_code: str, user_id: Optional[str] = None) -> ApprovalResponse:
        pl = ApprovalService._find_price_list(db, price_code)

        if not pl:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy bảng giá '{price_code}'")

        if pl.versions:
            for v in pl.versions:
                v.status = "SUBMITTED"
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

        if pl.versions:
            if act == "APPROVE":
                latest_v = ApprovalService._get_latest_version(pl)
                for v in pl.versions:
                    if latest_v and v.id != latest_v.id:
                        v.status = "SUPERSEDED"
                        v.approval_stage = "SUPERSEDED"
                    else:
                        v.status = target_status
                        v.approval_stage = target_stage
                        v.approved_by = approved_by_uuid
                        v.rejected_reason = None
            else:
                for v in pl.versions:
                    v.status = target_status
                    v.approval_stage = target_stage
                    v.rejected_reason = reason_text

        db.commit()
        db.refresh(pl)

        msg = "Phê duyệt thành công." if act == "APPROVE" else f"Từ chối thành công. Lý do: {reason_text}"
        return ApprovalService._build_approval_response(db=db, price_list=pl, message=msg)