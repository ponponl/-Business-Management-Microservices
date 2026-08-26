import re
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.models.pricing import PriceList, PriceListDetail, PriceListVersion, ServiceItem
from app.schemas.price_list import PriceListCreate

VN_TZ = timezone(timedelta(hours=7))

def get_current_vn_time() -> datetime:
    return datetime.now(VN_TZ).replace(tzinfo=None)

def safe_float(val: Any) -> float:
    if val is None: 
        return 0.0
    try: 
        return float(val)
    except (ValueError, TypeError): 
        return 0.0

def format_version(ver_num: Any) -> str:
    """Chuẩn hóa định dạng hiển thị version luôn là vX.0"""
    if ver_num is None: 
        return "v1.0"
    
    v_str = str(ver_num).strip()
    if not v_str:
        return "v1.0"
        
    if v_str.lower().startswith("v"):
        v_str = v_str[1:]
        
    try:
        num = float(v_str)
        return f"v{int(num)}.0"
    except (ValueError, TypeError):
        return f"v{v_str}" if "." in v_str else f"v{v_str}.0"

class PriceListService:

    @staticmethod
    def get_all_service_items(db: Session) -> List[Dict[str, Any]]:
        subquery = (
            db.query(
                PriceListDetail.service_item_id, 
                PriceListDetail.unit_price,
                func.row_number().over(
                    partition_by=PriceListDetail.service_item_id, 
                    order_by=[desc(PriceListDetail.id)]
                ).label("rn")
            ).subquery()
        )
        results = (
            db.query(ServiceItem, subquery.c.unit_price)
            .outerjoin(subquery, (ServiceItem.id == subquery.c.service_item_id) & (subquery.c.rn == 1))
            .filter(ServiceItem.status == "ACTIVE")
            .order_by(ServiceItem.service_name)
            .all()
        )
        return [
            {
                "id": str(srv.id), 
                "code": srv.service_code, 
                "serviceCode": srv.service_code, 
                "service_code": srv.service_code,
                "name": srv.service_name, 
                "serviceName": srv.service_name, 
                "service_name": srv.service_name,
                "unit": srv.unit or "", 
                "serviceGroup": srv.service_group or "", 
                "service_group": srv.service_group or "",
                "price": safe_float(up), 
                "unitPrice": safe_float(up), 
                "unit_price": safe_float(up)
            }
            for srv, up in results
        ]

    @staticmethod
    def _get_users_map_from_cache(db: Session, user_ids: set) -> Dict[str, str]:
        if not user_ids: 
            return {}
        clean_ids = [str(uid).strip().lower() for uid in user_ids if uid]
        try:
            from app.models.pricing import UserCache
            cached = db.query(UserCache).filter(UserCache.user_id.in_(clean_ids)).all()
            return {str(u.user_id).strip().lower(): getattr(u, "username", str(u.user_id)) for u in cached}
        except (ImportError, AttributeError):
            return {}

    @staticmethod
    def _validate_overlapping_time(
        db: Session, 
        scope_type: str, 
        scope_id: Optional[str], 
        effective_from: Optional[datetime], 
        effective_to: Optional[datetime], 
        exclude_price_list_id: Optional[Any] = None
    ):
        if not effective_from or not effective_to:
            raise HTTPException(status_code=400, detail="Ngày bắt đầu và ngày kết thúc hiệu lực là bắt buộc!")
        if effective_from > effective_to:
            raise HTTPException(status_code=400, detail="Ngày bắt đầu hiệu lực không được lớn hơn ngày kết thúc!")

        target_type = scope_type.strip().upper() if scope_type else "GENERAL"
        target_id = None if target_type == "GENERAL" else (scope_id.strip() if scope_id and str(scope_id).strip() != "" else None)

        query = db.query(PriceListVersion, PriceList).join(PriceList, PriceList.id == PriceListVersion.price_list_id).filter(
            func.upper(PriceList.scope_type) == target_type, 
            PriceListVersion.status.in_(["SUBMITTED", "APPROVED", "EFFECTIVE"])
        )
        query = query.filter(or_(PriceList.scope_id.is_(None), PriceList.scope_id == "")) if target_id is None else query.filter(PriceList.scope_id == target_id)
        if exclude_price_list_id: 
            query = query.filter(PriceList.id != exclude_price_list_id)

        new_from = datetime.combine(effective_from, datetime.min.time()) if not isinstance(effective_from, datetime) else effective_from
        new_to = datetime.combine(effective_to, datetime.max.time()) if not isinstance(effective_to, datetime) else effective_to

        for ver, pl in query.all():
            v_from = datetime.combine(ver.valid_from, datetime.min.time()) if ver.valid_from and not isinstance(ver.valid_from, datetime) else ver.valid_from
            v_to = datetime.combine(ver.valid_to, datetime.max.time()) if ver.valid_to and not isinstance(ver.valid_to, datetime) else ver.valid_to

            if ((v_to is None) or (new_from <= v_to)) and ((v_from is None) or (new_to >= v_from)):
                from_str = v_from.strftime("%d/%m/%Y") if v_from else "Không giới hạn"
                to_str = v_to.strftime("%d/%m/%Y") if v_to else "Không giới hạn"
                target_info = f" đối tượng '{target_id}'" if target_id else " đối tượng chung"
                raise HTTPException(
                    status_code=400, 
                    detail=f"Thời gian hiệu lực bị chồng lấp với bảng giá '{pl.price_list_name}' ({pl.price_list_code}) cùng loại {target_type}{target_info}! (từ {from_str} đến {to_str})."
                )

    @staticmethod
    def _generate_next_price_code(db: Session) -> str:
        prefix = f"PL-{get_current_vn_time().year}-"
        codes = db.query(PriceList.price_list_code).filter(PriceList.price_list_code.like(f"{prefix}%")).all()
        max_num = 0
        pattern = re.compile(rf"^{prefix}(\d+)$")
        for (code_val,) in codes:
            if code_val:
                m = pattern.match(code_val.strip())
                if m: 
                    max_num = max(max_num, int(m.group(1)))
        return f"{prefix}{max_num + 1:03d}"

    @staticmethod
    def _resolve_service_item_id(db: Session, item: Any) -> Optional[Any]:
        """Hàm rút gọn lấy service_item_id linh hoạt từ Dict hoặc Pydantic Object"""
        def get_val(key_list):
            if isinstance(item, dict):
                for k in key_list:
                    if k in item and item[k]: return item[k]
            else:
                for k in key_list:
                    val = getattr(item, k, None)
                    if val: return val
            return None

        # 1. Thử lấy ID trực tiếp
        raw_id = get_val(["service_item_id", "serviceItemId", "id"])
        if raw_id:
            try:
                # Kiểm tra nếu là UUID hợp lệ hoặc tồn tại trong DB
                srv = db.query(ServiceItem).filter(ServiceItem.id == raw_id).first()
                if srv: 
                    return srv.id
            except Exception:
                pass

        # 2. Fallback: Tìm theo service_code
        code = get_val(["service_code", "serviceCode", "code"])
        if code:
            srv = db.query(ServiceItem).filter(ServiceItem.service_code == str(code).strip()).first()
            if srv: 
                return srv.id

        # 3. Fallback: Tìm theo service_name
        name = get_val(["service_name", "serviceName", "name"])
        if name:
            srv = db.query(ServiceItem).filter(ServiceItem.service_name == str(name).strip()).first()
            if srv: 
                return srv.id

        return None

    @staticmethod
    def get_stats(db: Session) -> Dict[str, int]:
        subquery = db.query(
            PriceListVersion.price_list_id, 
            func.max(PriceListVersion.version_number).label("max_ver")
        ).group_by(PriceListVersion.price_list_id).subquery()
        
        latest = db.query(PriceListVersion).join(
            subquery, 
            (PriceListVersion.price_list_id == subquery.c.price_list_id) & (PriceListVersion.version_number == subquery.c.max_ver)
        ).all()
        
        stats = {"total": db.query(PriceList).count(), "submitted": 0, "approved": 0, "effective": 0, "rejected": 0}
        for ver in latest:
            st = str(ver.status or "").strip().lower()
            if st in stats: 
                stats[st] += 1
        return stats

    @staticmethod
    def get_paginated_list(
        db: Session, 
        status_filter: Optional[str] = None, 
        apply_type: Optional[str] = None, 
        customer: Optional[str] = None, 
        search: Optional[str] = None, 
        page: int = 1, 
        page_size: int = 10, 
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            query = db.query(PriceList, PriceListVersion).join(PriceListVersion, PriceList.id == PriceListVersion.price_list_id)
            if status_filter and status_filter != "Tất cả": 
                query = query.filter(PriceListVersion.status.ilike(status_filter.strip()))
            if apply_type and apply_type != "Tất cả": 
                query = query.filter(PriceList.scope_type.ilike(apply_type.strip()))
            if customer and customer != "Tất cả": 
                query = query.filter(PriceList.price_list_name.ilike(f"%{customer.strip()}%"))
            if search and search.strip():
                sterm = f"%{search.strip()}%"
                query = query.filter(or_(PriceList.price_list_code.ilike(sterm), PriceList.price_list_name.ilike(sterm), PriceList.scope_id.ilike(sterm)))

            total_count = query.count()
            records = query.order_by(desc(PriceListVersion.version_number), desc(PriceList.created_at)).offset((page - 1) * page_size).limit(page_size).all()

            user_ids = {str(getattr(pl, "created_by", None) or getattr(ver, "created_by", None)).strip() for pl, ver in records if (getattr(pl, "created_by", None) or getattr(ver, "created_by", None))}
            users_map = PriceListService._get_users_map_from_cache(db, user_ids)

            items = []
            for pl, ver in records:
                vf, vt = getattr(ver, "valid_from", None), getattr(ver, "valid_to", None)
                s_str = vf.strftime("%d/%m/%Y") if hasattr(vf, "strftime") else ""
                e_str = vt.strftime("%d/%m/%Y") if hasattr(vt, "strftime") else ""
                eff_time = f"{s_str} - {e_str}" if s_str and e_str else (f"Từ {s_str}" if s_str else "N/A")

                at_val = getattr(pl, "updated_at", None) or getattr(pl, "created_at", None) or getattr(ver, "updated_at", None) or getattr(ver, "created_at", None)
                at_str = at_val.strftime("%d/%m/%Y %H:%M") if hasattr(at_val, "strftime") else "N/A"
                reason = getattr(ver, "rejected_reason", None) or getattr(ver, "rejection_reason", None) or getattr(ver, "reject_reason", None) or getattr(ver, "rejection_note", None) or ""

                cid = str(getattr(pl, "created_by", None) or getattr(ver, "created_by", None) or "").strip().lower()
                creator = users_map.get(cid, "Nhân viên" if (re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", cid) or not cid or cid == "none") else cid)

                items.append({
                    "id": str(pl.price_list_code or pl.id), 
                    "priceCode": str(pl.price_list_code or pl.id), 
                    "price_code": str(pl.price_list_code or pl.id),
                    "name": str(pl.price_list_name or "N/A"), 
                    "contractId": str(getattr(pl, "scope_id", None) or getattr(pl, "contract_id", None) or "N/A"),
                    "type": str(pl.scope_type or "GENERAL").upper(), 
                    "version": format_version(getattr(ver, "version_number", 1)),
                    "effectiveTime": eff_time, 
                    "status": str(ver.status or "DRAFT").upper(), 
                    "rejectReason": str(reason), 
                    "rejectionReason": str(reason),
                    "updatedBy": creator, 
                    "updatedAt": at_str
                })

            customers = ["Tất cả"] + [c[0] for c in db.query(PriceList.price_list_name).filter(PriceList.price_list_name.isnot(None)).distinct().all() if c[0]]
            types = ["Tất cả", "CUSTOMER", "CONTRACT", "GENERAL", "SERVICE_GROUP", "SERVICE_TYPE"]
            return {"items": items, "total": total_count, "page": page, "page_size": page_size, "available_types": types, "available_customers": customers}

        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Lỗi Server: {str(e)}")

    @staticmethod
    def get_detail_by_code(db: Session, price_code: str) -> Dict[str, Any]:
        conds = [PriceList.price_list_code == price_code]
        try:
            uuid.UUID(price_code)
            conds.append(PriceList.id == price_code)
        except ValueError: 
            pass

        record = db.query(PriceList, PriceListVersion).join(PriceListVersion, PriceList.id == PriceListVersion.price_list_id).filter(or_(*conds)).order_by(desc(PriceListVersion.status == "REJECTED"), desc(PriceListVersion.version_number), desc(PriceListVersion.id)).first()
        if not record: 
            raise HTTPException(status_code=404, detail=f"Không tìm thấy bảng giá '{price_code}'")

        pl, ver = record
        vf, vt = getattr(ver, "valid_from", None), getattr(ver, "valid_to", None)
        vf_str = vf.strftime("%Y-%m-%d") if hasattr(vf, "strftime") else ""
        vt_str = vt.strftime("%Y-%m-%d") if hasattr(vt, "strftime") else ""

        services_data = [
            {
                "serviceItemId": str(srv.id) if srv else None, 
                "service_item_id": str(srv.id) if srv else None,
                "code": srv.service_code if srv else "SRV-DEFAULT", 
                "serviceCode": srv.service_code if srv else "SRV-DEFAULT", 
                "service_code": srv.service_code if srv else "SRV-DEFAULT",
                "name": srv.service_name if srv else "Dịch vụ định mức", 
                "serviceName": srv.service_name if srv else "Dịch vụ định mức", 
                "service_name": srv.service_name if srv else "Dịch vụ định mức",
                "unit": srv.unit if srv else "Lượt", 
                "serviceGroup": getattr(srv, "service_group", "") if srv else "", 
                "service_group": getattr(srv, "service_group", "") if srv else "",
                "price": safe_float(item.unit_price), 
                "unitPrice": safe_float(item.unit_price), 
                "unit_price": safe_float(item.unit_price)
            }
            for item in db.query(PriceListDetail).filter(PriceListDetail.price_list_version_id == ver.id).all() for srv in [item.service_item]
        ]
        reason = getattr(ver, "rejected_reason", None) or getattr(ver, "rejection_reason", None) or getattr(ver, "reject_reason", None) or getattr(ver, "rejection_note", None) or getattr(pl, "rejected_reason", None) or getattr(pl, "rejection_reason", None) or ""
        scope_id = str(getattr(pl, "scope_id", None) or getattr(pl, "contract_id", None) or getattr(pl, "customer_id", None) or "")

        return {
            "id": pl.price_list_code or str(pl.id), 
            "priceCode": pl.price_list_code or "N/A", 
            "price_code": pl.price_list_code or "N/A",
            "priceName": pl.price_list_name or "N/A", 
            "price_name": pl.price_list_name or "N/A",
            "scopeType": str(pl.scope_type or "CUSTOMER"), 
            "scope_type": str(pl.scope_type or "CUSTOMER"), 
            "targetType": str(pl.scope_type or "CUSTOMER"), 
            "target_type": str(pl.scope_type or "CUSTOMER"),
            "scopeId": scope_id or "N/A", 
            "scope_id": scope_id or "N/A", 
            "specificTarget": scope_id, 
            "specific_target": scope_id,
            "version": format_version(getattr(ver, "version_number", 1)), 
            "status": str(ver.status or "DRAFT").upper(),
            "rejectReason": reason, 
            "rejectionReason": reason, 
            "validFrom": vf_str, 
            "validTo": vt_str,
            "effectiveFrom": vf_str, 
            "effective_from": vf_str, 
            "effectiveTo": vt_str, 
            "effective_to": vt_str, 
            "services": services_data
        }

    @staticmethod
    def create_price_list(db: Session, payload: PriceListCreate, current_user: Optional[CurrentUser] = None) -> Dict[str, Any]:
        try:
            status_upper = payload.status.upper() if payload.status else "DRAFT"
            if status_upper != "DRAFT":
                PriceListService._validate_overlapping_time(
                    db=db, 
                    scope_type=payload.target_type, 
                    scope_id=payload.specific_target, 
                    effective_from=payload.effective_from, 
                    effective_to=payload.effective_to
                )

            price_code = payload.price_code or PriceListService._generate_next_price_code(db)
            user_id, now = (current_user.id if current_user else None), get_current_vn_time()
            scope_id_val = payload.specific_target.strip() if (payload.target_type != "GENERAL" and payload.specific_target) else None

            # 1. Lưu thông tin chung vào PriceList
            new_price_list = PriceList(
                price_list_code=price_code, 
                price_list_name=payload.price_name, 
                scope_type=payload.target_type, 
                scope_id=scope_id_val
            )
            for attr in ["created_at", "updated_at"]: 
                if hasattr(new_price_list, attr): 
                    setattr(new_price_list, attr, now)
            for attr in ["created_by", "changed_by"]: 
                if hasattr(new_price_list, attr): 
                    setattr(new_price_list, attr, user_id)
            
            db.add(new_price_list)
            db.flush()

            # 2. Lưu phiên bản vào PriceListVersion
            new_version = PriceListVersion(
                price_list_id=new_price_list.id, 
                version_number="v1.0", 
                status=status_upper, 
                valid_from=payload.effective_from, 
                valid_to=payload.effective_to
            )
            for attr in ["created_at", "updated_at"]: 
                if hasattr(new_version, attr): 
                    setattr(new_version, attr, now)
            if hasattr(new_version, "created_by"): 
                new_version.created_by = user_id
            
            db.add(new_version)
            db.flush()

            # 3. Ghi ĐƠN GIÁ vào PriceListDetail với hàm tra cứu tự động
            for item in payload.services:
                target_service_id = PriceListService._resolve_service_item_id(db, item)
                
                # Nếu không thể xác định dịch vụ trong DB thì bỏ qua
                if not target_service_id:
                    continue

                # Lấy giá linh hoạt theo các kiểu đặt tên
                if isinstance(item, dict):
                    price_raw = item.get("price", item.get("unit_price", item.get("unitPrice", 0.0)))
                else:
                    price_raw = getattr(item, "price", getattr(item, "unit_price", getattr(item, "unitPrice", 0.0)))

                unit_price_val = safe_float(price_raw)

                detail = PriceListDetail(
                    price_list_id=new_price_list.id,
                    price_list_version_id=new_version.id,
                    service_item_id=target_service_id,
                    unit_price=unit_price_val
                )
                if hasattr(detail, "created_at"): 
                    detail.created_at = now
                db.add(detail)

            db.commit()
            return {"id": new_price_list.price_list_code, "priceCode": new_price_list.price_list_code, "message": "Tạo mới bảng giá thành công"}
        except HTTPException: 
            db.rollback()
            raise
        except Exception as e: 
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Lỗi tạo bảng giá: {str(e)}")

    @staticmethod
    def update_price_list(db: Session, price_code: str, payload: PriceListCreate, current_user: Optional[CurrentUser] = None) -> Dict[str, Any]:
        conds = [PriceList.price_list_code == price_code]
        try: 
            conds.append(PriceList.id == uuid.UUID(price_code))
        except ValueError: 
            pass

        record = db.query(PriceList, PriceListVersion).join(PriceListVersion, PriceList.id == PriceListVersion.price_list_id).filter(or_(*conds)).order_by(desc(PriceListVersion.version_number)).first()
        if not record: 
            raise HTTPException(status_code=404, detail=f"Không tìm thấy bảng giá '{price_code}'")

        pl, ver = record
        current_status = str(ver.status or "").upper()
        if current_status not in ["DRAFT", "REJECTED"]:
            raise HTTPException(status_code=400, detail=f"Không thể chỉnh sửa bảng giá ở trạng thái '{current_status}'.")

        status_upper = payload.status.upper() if payload.status else current_status
        if status_upper != "DRAFT":
            PriceListService._validate_overlapping_time(
                db=db, 
                scope_type=payload.target_type, 
                scope_id=payload.specific_target, 
                effective_from=payload.effective_from, 
                effective_to=payload.effective_to, 
                exclude_price_list_id=pl.id
            )

        try:
            user_id, now = (current_user.id if current_user else None), get_current_vn_time()
            pl.price_list_name, pl.scope_type = payload.price_name, payload.target_type
            pl.scope_id = payload.specific_target.strip() if (payload.target_type != "GENERAL" and payload.specific_target) else None
            if hasattr(pl, "updated_at"): 
                pl.updated_at = now
            if hasattr(pl, "changed_by"): 
                pl.changed_by = user_id

            ver.valid_from, ver.valid_to, ver.status = payload.effective_from, payload.effective_to, status_upper
            if hasattr(ver, "updated_at"): 
                ver.updated_at = now
            if hasattr(ver, "changed_by"): 
                ver.changed_by = user_id
            for f in ["rejected_reason", "rejection_reason", "reject_reason", "rejection_note"]:
                if hasattr(ver, f): 
                    setattr(ver, f, None)

            # Xóa chi tiết bảng giá cũ
            db.query(PriceListDetail).filter(PriceListDetail.price_list_version_id == ver.id).delete(synchronize_session=False)

            # Cập nhật chi tiết bảng giá mới với hàm tra cứu tự động
            for item in payload.services:
                target_service_id = PriceListService._resolve_service_item_id(db, item)
                
                if not target_service_id:
                    continue

                if isinstance(item, dict):
                    price_raw = item.get("price", item.get("unit_price", item.get("unitPrice", 0.0)))
                else:
                    price_raw = getattr(item, "price", getattr(item, "unit_price", getattr(item, "unitPrice", 0.0)))

                unit_price_val = safe_float(price_raw)

                detail = PriceListDetail(
                    price_list_id=pl.id, 
                    price_list_version_id=ver.id, 
                    service_item_id=target_service_id, 
                    unit_price=unit_price_val
                )
                for attr in ["created_at", "updated_at"]: 
                    if hasattr(detail, attr): 
                        setattr(detail, attr, now)
                db.add(detail)

            db.commit()
            return {"id": pl.price_list_code, "priceCode": pl.price_list_code, "message": "Cập nhật bảng giá thành công"}
        except HTTPException: 
            db.rollback()
            raise
        except Exception as e: 
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Lỗi khi cập nhật bảng giá: {str(e)}")