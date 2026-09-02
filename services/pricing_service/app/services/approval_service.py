import uuid
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func, desc
from fastapi import HTTPException

from app.models.pricing import PriceList, PriceListVersion, PriceListDetail, UserCache
from app.schemas.approval import ApprovalActionRequest, ApprovalResponse

VN_TZ = timezone(timedelta(hours=7))


def get_current_vn_time() -> datetime:
    return datetime.now(VN_TZ).replace(tzinfo=None)


def safe_parse_uuid(val: Optional[Any]) -> Optional[uuid.UUID]:
    if not val:
        return None
    try:
        return uuid.UUID(str(val).strip())
    except (ValueError, AttributeError):
        return None


class ApprovalService:

    @staticmethod
    def _get_latest_version(price_list: PriceList) -> Optional[PriceListVersion]:
        if not price_list or not getattr(price_list, "versions", None):
            return None

        def parse_version_key(v: PriceListVersion):
            raw_ver = str(getattr(v, "version_number", "1.0") or "1.0").strip().lstrip("vV")
            try:
                version_numbers = [int(num) for num in raw_ver.split(".") if num.isdigit()]
            except Exception:
                version_numbers = [0, 0]

            if not version_numbers:
                version_numbers = [0, 0]

            c_at = getattr(v, "created_at", None)
            if c_at and hasattr(c_at, "tzinfo") and c_at.tzinfo is not None:
                c_at = c_at.replace(tzinfo=None)
            created_at = c_at or datetime.min

            return (tuple(version_numbers), created_at)

        return max(price_list.versions, key=parse_version_key)

    @staticmethod
    def _resolve_user_name(db: Session, user_id_val: Optional[Any]) -> str:
        if not user_id_val:
            return "Staff"
        u_str = str(user_id_val).strip().lower()
        if not u_str or u_str == "none":
            return "Staff"

        user_cache = db.query(UserCache).filter(func.lower(UserCache.user_id) == u_str).first()
        if user_cache:
            return user_cache.full_name or user_cache.username or u_str
        return u_str if len(u_str) < 20 else "Staff"

    @staticmethod
    def get_approval_stats(db: Session) -> Dict[str, int]:
        price_lists = db.query(PriceList).options(
            joinedload(PriceList.versions)
        ).filter(
            or_(PriceList.is_deleted == False, PriceList.is_deleted == None)
        ).all()

        stats = {"total": 0, "submitted": 0, "approved": 0, "effective": 0, "rejected": 0}

        for pl in price_lists:
            latest_v = ApprovalService._get_latest_version(pl)
            if not latest_v:
                continue

            stats["total"] += 1
            st = str(getattr(latest_v, "status", "")).strip().upper()
            if hasattr(latest_v.status, "value"):
                st = str(latest_v.status.value).strip().upper()

            if st == "SUBMITTED":
                stats["submitted"] += 1
            elif st == "APPROVED":
                stats["approved"] += 1
            elif st == "EFFECTIVE":
                stats["effective"] += 1
            elif st == "REJECTED":
                stats["rejected"] += 1

        return stats

    @staticmethod
    def get_director_approval_stats(db: Session) -> Dict[str, int]:
        price_lists = db.query(PriceList).options(
            joinedload(PriceList.versions)
        ).filter(
            or_(PriceList.is_deleted == False, PriceList.is_deleted == None)
        ).all()

        stats = {"total": 0, "approved": 0, "effective": 0, "rejected": 0}

        for pl in price_lists:
            latest_v = ApprovalService._get_latest_version(pl)
            if not latest_v:
                continue

            st = str(getattr(latest_v, "status", "")).strip().upper()
            if hasattr(latest_v.status, "value"):
                st = str(latest_v.status.value).strip().upper()

            if st in ["APPROVED", "EFFECTIVE", "REJECTED"]:
                stats["total"] += 1
                if st == "APPROVED":
                    stats["approved"] += 1
                elif st == "EFFECTIVE":
                    stats["effective"] += 1
                elif st == "REJECTED":
                    stats["rejected"] += 1

        return stats

    @staticmethod
    def _extract_services_from_version(db: Session, version: Optional[PriceListVersion], price_list: PriceList) -> List[dict]:
        query = db.query(PriceListDetail).options(joinedload(PriceListDetail.service_item))

        if version:
            query = query.filter(PriceListDetail.price_list_version_id == version.id)
        else:
            query = query.filter(PriceListDetail.price_list_id == price_list.id)

        services_data = []
        for d in query.all():
            srv = d.service_item
            code = getattr(srv, "service_code", None) or getattr(srv, "code", None) or getattr(d, "service_code", None) or (str(d.service_id) if getattr(d, "service_id", None) else None) or "-"
            name = getattr(srv, "service_name", None) or getattr(srv, "name", None) or getattr(d, "service_name", None) or getattr(d, "description", None) or "Dịch vụ chuẩn"
            unit = getattr(d, "unit", None) or getattr(srv, "unit", None) or "Lượt"
            price = float(d.unit_price) if getattr(d, "unit_price", None) is not None else 0.0

            services_data.append({
                "service_code": str(code), "serviceCode": str(code), "code": str(code),
                "service_name": str(name), "serviceName": str(name), "name": str(name), "title": str(name),
                "unit": str(unit), "price": price, "unit_price": price, "unitPrice": price
            })
        return services_data

    @staticmethod
    def _build_version_approval_response(db: Session, price_list: PriceList, version: PriceListVersion, message: str) -> ApprovalResponse:
        price_code = price_list.price_list_code or str(price_list.id)

        # Lấy ưu tiên các trường tên trong PriceListVersion trước, bao gồm price_list_name
        ver_name = (
            getattr(version, "price_list_name", None) or
            getattr(version, "version_price_name", None) or
            getattr(version, "version_name", None) or
            getattr(version, "price_name", None) or
            getattr(version, "name", None) or
            getattr(price_list, "price_list_name", None) or ""
        )

        valid_from_val = getattr(version, "valid_from", None) or getattr(price_list, "valid_from", None)
        valid_to_val = getattr(version, "valid_to", None) or getattr(price_list, "valid_to", None)

        valid_from_str = valid_from_val.strftime("%d/%m/%Y") if valid_from_val else None
        valid_to_str = valid_to_val.strftime("%d/%m/%Y") if valid_to_val else None

        action_time_val = getattr(version, "created_at", None) or getattr(price_list, "updated_at", None)
        updated_at_str = action_time_val.strftime("%H:%M %d/%m/%Y") if action_time_val else None

        st_raw = getattr(version, "status", "DRAFT") if version else "DRAFT"
        status_val = str(st_raw.value if hasattr(st_raw, "value") else st_raw).strip().upper()

        stg_raw = getattr(version, "approval_stage", "DRAFT") if version else "DRAFT"
        stage_val = str(stg_raw.value if hasattr(stg_raw, "value") else stg_raw).strip().upper()

        ver_num = version.version_number if (version and version.version_number) else "1.0"
        ver_clean = str(ver_num).strip().lstrip("vV")
        version_str = f"v{ver_clean if ver_clean else '1.0'}"

        scope_raw = getattr(price_list, "scope_type", "GENERAL")
        target_type = str(scope_raw.value if hasattr(scope_raw, "value") else scope_raw).strip().upper() if scope_raw else "GENERAL"

        if target_type in ["CUSTOMER", "CUSTOMER_SPECIFIC"] and getattr(price_list, "customer_id", None):
            specific_target = str(price_list.customer_id)
        elif target_type in ["CONTRACT", "CONTRACT_SPECIFIC"] and getattr(price_list, "contract_id", None):
            specific_target = str(price_list.contract_id)
        else:
            specific_target = str(price_list.scope_id) if getattr(price_list, "scope_id", None) else None

        user_id_to_lookup = version.approved_by if (version and getattr(version, "approved_by", None)) else (version.created_by if version else getattr(price_list, "created_by", None))
        
        reason = getattr(version, "rejected_reason", None) or getattr(version, "rejection_reason", None) or ""

        return ApprovalResponse(
            price_list_id=str(price_list.id),
            price_list_code=price_code,
            price_code=price_code,

            price_name=ver_name, 
            version_price_name=ver_name,
            version_name=ver_name,

            target_type=target_type,
            specific_target=specific_target,
            version=version_str,
            version_number=version_str,
            effective_from=valid_from_str,
            effective_to=valid_to_str,
            status=status_val,
            approval_stage=stage_val,
            rejected_reason=reason,
            updated_by=ApprovalService._resolve_user_name(db, user_id_to_lookup),
            updated_at=updated_at_str,
            message=message,
            services=ApprovalService._extract_services_from_version(db, version, price_list)
        )

    @staticmethod
    def get_approval_list(db: Session, status: Optional[str] = None) -> List[ApprovalResponse]:
        price_lists = db.query(PriceList).options(
            joinedload(PriceList.versions)
        ).filter(
            or_(PriceList.is_deleted == False, PriceList.is_deleted == None)
        ).all()

        clean_status = status.strip().upper() if status and status.strip() else None

        results = []
        for pl in price_lists:
            latest_ver = ApprovalService._get_latest_version(pl)
            if not latest_ver:
                continue
            
            res = ApprovalService._build_version_approval_response(db=db, price_list=pl, version=latest_ver, message="Lấy thông tin thành công")
            if not clean_status or clean_status in ["TẤT CẢ", "ALL"] or res.status.upper() == clean_status:
                results.append(res)
                
        results.sort(key=lambda x: x.updated_at or "", reverse=True)
        return results

    @staticmethod
    def get_director_approval_list(db: Session, status: Optional[str] = None) -> List[ApprovalResponse]:
        price_lists = db.query(PriceList).options(
            joinedload(PriceList.versions)
        ).filter(
            or_(PriceList.is_deleted == False, PriceList.is_deleted == None)
        ).all()

        clean_status = status.strip().upper() if status and status.strip() else None
        ALLOWED_STATUSES = ["APPROVED", "EFFECTIVE", "REJECTED"]

        results = []
        for pl in price_lists:
            latest_ver = ApprovalService._get_latest_version(pl)
            if not latest_ver:
                continue

            res = ApprovalService._build_version_approval_response(db=db, price_list=pl, version=latest_ver, message="Lấy thông tin thành công")
            if res.status in ALLOWED_STATUSES:
                if not clean_status or clean_status in ["TẤT CẢ", "ALL"] or res.status.upper() == clean_status:
                    results.append(res)

        results.sort(key=lambda x: x.updated_at or "", reverse=True)
        return results

    @staticmethod
    def _find_price_list(db: Session, price_code: str) -> Optional[PriceList]:
        is_valid_uuid = safe_parse_uuid(price_code) is not None

        conditions = [PriceList.price_list_code == price_code]
        if is_valid_uuid:
            conditions.append(PriceList.id == price_code)

        return db.query(PriceList).options(
            joinedload(PriceList.versions)
        ).filter(
            or_(PriceList.is_deleted == False, PriceList.is_deleted == None), or_(*conditions)
        ).first()

    @staticmethod
    def get_price_list_versions(db: Session, price_code: str) -> List[Dict[str, Any]]:
        pl = ApprovalService._find_price_list(db, price_code)
        if not pl:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy bảng giá '{price_code}'")

        versions_list = []
        sorted_versions = sorted(
            pl.versions or [], 
            key=lambda v: getattr(v, "created_at", datetime.min) or datetime.min, 
            reverse=True
        )

        for v in sorted_versions:
            ver_num = str(v.version_number or "1.0").strip().lstrip("vV")
            ver_str = f"v{ver_num}"
            st_raw = getattr(v, "status", "DRAFT")
            status_val = str(st_raw.value if hasattr(st_raw, "value") else st_raw).strip().upper()
            
            created_at = getattr(v, "created_at", None)
            created_at_str = created_at.strftime("%H:%M %d/%m/%Y") if created_at else None

            versions_list.append({
                "id": str(v.id),
                "version": ver_str,
                "version_number": ver_str,
                "status": status_val,
                "approval_stage": str(getattr(v, "approval_stage", "")),
                "rejected_reason": getattr(v, "rejected_reason", "") or getattr(v, "rejection_reason", "") or "",
                "created_at": created_at_str,
                "created_by": ApprovalService._resolve_user_name(db, v.created_by)
            })

        return versions_list

    @staticmethod
    def get_approval_detail(db: Session, price_code: str, version_str: Optional[str] = None) -> ApprovalResponse:
        pl = ApprovalService._find_price_list(db, price_code)
        if not pl:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy bảng giá '{price_code}'")

        target_version = None
        if version_str:
            clean_ver = version_str.strip().lstrip("vV")
            for v in (pl.versions or []):
                v_num = str(v.version_number or "").strip().lstrip("vV")
                if v_num == clean_ver:
                    target_version = v
                    break

        if not target_version:
            target_version = ApprovalService._get_latest_version(pl)

        return ApprovalService._build_version_approval_response(
            db=db, price_list=pl, version=target_version, message="Lấy chi tiết thành công"
        )

    @staticmethod
    def submit_for_approval(db: Session, price_code: str, user_id: Optional[str] = None) -> ApprovalResponse:
        pl = ApprovalService._find_price_list(db, price_code)
        if not pl:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy bảng giá '{price_code}'")

        now_vn = get_current_vn_time()
        pl.updated_at = now_vn
        latest_v = ApprovalService._get_latest_version(pl)
        user_uuid = safe_parse_uuid(user_id)

        if latest_v and str(latest_v.status).upper() == "REJECTED":
            curr_ver_str = str(latest_v.version_number or "1.0").strip().lstrip("vV")
            parts = curr_ver_str.split(".")

            try:
                major = int(parts[0])
                minor = int(parts[1]) + 1 if len(parts) > 1 else 1
            except (ValueError, IndexError):
                major, minor = 1, 1

            new_ver_num = f"{major}.{minor}"

            active_version = PriceListVersion(
                id=uuid.uuid4(),
                price_list_id=pl.id,
                version_number=new_ver_num,
                valid_from=latest_v.valid_from,
                valid_to=latest_v.valid_to,
                status="SUBMITTED",
                approval_stage="MANAGER_PENDING",
                parent_version_id=latest_v.id,
                created_by=user_uuid,
                created_at=now_vn
            )
            
            if hasattr(active_version, "price_list_name"):
                active_version.price_list_name = getattr(latest_v, "price_list_name", pl.price_list_name)

            db.add(active_version)
            db.flush()

            old_details = db.query(PriceListDetail).filter(PriceListDetail.price_list_version_id == latest_v.id).all()
            for detail in old_details:
                db.add(PriceListDetail(
                    id=uuid.uuid4(),
                    price_list_id=pl.id,
                    price_list_version_id=active_version.id,
                    service_item_id=detail.service_item_id,
                    unit_price=detail.unit_price
                ))

        elif latest_v:
            latest_v.status = "SUBMITTED"
            latest_v.approval_stage = "MANAGER_PENDING"
            active_version = latest_v
        else:
            active_version = PriceListVersion(
                id=uuid.uuid4(),
                price_list_id=pl.id,
                version_number="1.0",
                status="SUBMITTED",
                approval_stage="MANAGER_PENDING",
                created_by=user_uuid,
                created_at=now_vn
            )
            db.add(active_version)

        db.commit()
        db.refresh(pl)
        return ApprovalService._build_version_approval_response(db=db, price_list=pl, version=active_version, message="Đã gửi phê duyệt bảng giá thành công.")

    @staticmethod
    def manager_approve(db: Session, price_code: str, payload: ApprovalActionRequest, manager_id: Optional[str] = None) -> ApprovalResponse:
        act = payload.action.upper()
        if act not in ["APPROVE", "REJECT"]:
            raise HTTPException(status_code=400, detail="Hành động không hợp lệ.")

        pl = ApprovalService._find_price_list(db, price_code)
        if not pl:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy bảng giá '{price_code}'")

        latest_v = ApprovalService._get_latest_version(pl)
        if not latest_v:
            raise HTTPException(status_code=400, detail="Bảng giá chưa có phiên bản nào để duyệt.")

        if latest_v.status != "SUBMITTED":
            raise HTTPException(status_code=400, detail=f"Không thể duyệt phiên bản ở trạng thái '{latest_v.status}'.")

        now_vn = get_current_vn_time()
        pl.updated_at = now_vn
        reason_text = payload.rejected_reason or payload.comment or ""
        approved_by_uuid = safe_parse_uuid(manager_id)

        if act == "APPROVE":
            latest_v.status = "APPROVED"
            latest_v.approval_stage = "DIRECTOR_PENDING"
            latest_v.approved_by = approved_by_uuid
            latest_v.rejected_reason = None
        else:
            latest_v.status = "REJECTED"
            latest_v.approval_stage = "REJECTED"
            latest_v.rejected_reason = reason_text

        db.commit()
        db.refresh(pl)
        msg = "Quản lý phê duyệt thành công." if act == "APPROVE" else f"Từ chối thành công. Lý do: {reason_text}"
        return ApprovalService._build_version_approval_response(db=db, price_list=pl, version=latest_v, message=msg)

    @staticmethod
    def director_approve(db: Session, price_code: str, payload: ApprovalActionRequest, director_id: Optional[str] = None) -> ApprovalResponse:
        act = payload.action.upper()
        if act not in ["APPROVE", "REJECT"]:
            raise HTTPException(status_code=400, detail="Hành động không hợp lệ.")

        pl = ApprovalService._find_price_list(db, price_code)
        if not pl:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy bảng giá '{price_code}'")

        latest_v = ApprovalService._get_latest_version(pl)
        if not latest_v:
            raise HTTPException(status_code=400, detail="Bảng giá chưa có phiên bản nào để duyệt.")

        if latest_v.status != "APPROVED":
            raise HTTPException(status_code=400, detail="Giám đốc chỉ có thể duyệt phiên bản đã qua Quản lý phê duyệt (APPROVED).")

        now_vn = get_current_vn_time()
        pl.updated_at = now_vn
        reason_text = payload.rejected_reason or payload.comment or ""
        approved_by_uuid = safe_parse_uuid(director_id)

        if act == "APPROVE":
            for v in pl.versions:
                if v.id != latest_v.id and v.status == "EFFECTIVE":
                    v.status = "SUPERSEDED"
                    v.approval_stage = "SUPERSEDED"
                    if latest_v.valid_from:
                        v.valid_to = latest_v.valid_from

            latest_v.status = "EFFECTIVE"
            latest_v.approval_stage = "COMPLETED"
            latest_v.approved_by = approved_by_uuid
            latest_v.rejected_reason = None
        else:
            latest_v.status = "REJECTED"
            latest_v.approval_stage = "REJECTED"
            latest_v.rejected_reason = reason_text

        db.commit()
        db.refresh(pl)
        msg = "Giám đốc phê duyệt thành công." if act == "APPROVE" else f"Từ chối thành công. Lý do: {reason_text}"
        return ApprovalService._build_version_approval_response(db=db, price_list=pl, version=latest_v, message=msg)