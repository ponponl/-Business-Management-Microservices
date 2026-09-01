import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

from fastapi import HTTPException, status
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session, joinedload

from app.api.deps import CurrentUser
from app.models.pricing import PriceList, PriceListDetail, PriceListVersion, ServiceItem, PriceChangeHistory
from app.schemas.price_list import PriceListCreate

from datetime import datetime
from dateutil.parser import parse as parse_date

VN_TZ = timezone(timedelta(hours=7))


def get_current_vn_time() -> datetime:
    return datetime.now(VN_TZ).replace(tzinfo=None)


def safe_float(val: Any) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    
    val_str = str(val).strip()
    if not val_str:
        return 0.0

    try:
        if '.' in val_str and ',' in val_str:
            if val_str.rfind('.') > val_str.rfind(','):
                val_str = val_str.replace(',', '')
            else:
                val_str = val_str.replace('.', '').replace(',', '.')
        elif '.' in val_str:
            parts = val_str.split('.')
            if len(parts[-1]) == 3 and len(parts) > 1:
                val_str = val_str.replace('.', '')
        elif ',' in val_str:
            parts = val_str.split(',')
            if len(parts[-1]) == 3 and len(parts) > 1:
                val_str = val_str.replace(',', '')
            else:
                val_str = val_str.replace(',', '.')

        clean_str = re.sub(r'[^\d.-]', '', val_str)
        return float(clean_str) if clean_str else 0.0
    except (ValueError, TypeError):
        return 0.0


def parse_version_tuple(ver_str: Any) -> Tuple[int, int]:
    """Phân tích chuỗi version thành tuple (major, minor)"""
    if not ver_str:
        return (1, 0)
    clean_str = str(ver_str).strip().lstrip("vV")
    numbers = [int(n) for n in re.findall(r'\d+', clean_str)]
    if not numbers:
        return (1, 0)
    if len(numbers) == 1:
        return (numbers[0], 0)
    return (numbers[0], numbers[1])


def format_version(ver_num: Any) -> str:
    """Định dạng hiển thị phiên bản chuẩn vX.Y"""
    major, minor = parse_version_tuple(ver_num)
    return f"v{major}.{minor}"


class PriceListService:

    @staticmethod
    def _get_latest_version(price_list: PriceList) -> Optional[PriceListVersion]:
        """Lấy phiên bản mới nhất - Đồng bộ chuẩn xác theo tuple version và created_at"""
        if not price_list or not getattr(price_list, "versions", None):
            return None

        def parse_version_key(v: PriceListVersion):
            version_tuple = parse_version_tuple(getattr(v, "version_number", "1.0"))
            c_at = getattr(v, "created_at", None)
            if c_at and hasattr(c_at, "tzinfo") and c_at.tzinfo is not None:
                c_at = c_at.replace(tzinfo=None)
            created_at = c_at or datetime.min
            return (version_tuple, created_at)

        return max(price_list.versions, key=parse_version_key)

    @staticmethod
    def _generate_next_version_number(latest_ver_num: str) -> str:
        """Tăng số version minor lên 1 (ví dụ: 1.0 -> 1.1)"""
        major, minor = parse_version_tuple(latest_ver_num)
        return f"{major}.{minor + 1}"

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
                "serviceGroup": getattr(srv, "service_group", "") or "",
                "service_group": getattr(srv, "service_group", "") or "",
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
            cached = db.query(UserCache).filter(func.lower(UserCache.user_id).in_(clean_ids)).all()
            return {
                str(u.user_id).strip().lower(): (getattr(u, "full_name", None) or getattr(u, "username", None) or str(u.user_id))
                for u in cached
            }
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
    def _ensure_valid_price_code(db: Session, pl: PriceList) -> str:
        if pl.price_list_code and str(pl.price_list_code).strip() and not str(pl.price_list_code).startswith("None"):
            return str(pl.price_list_code).strip()

        new_code = PriceListService._generate_next_price_code(db)
        pl.price_list_code = new_code
        pl.updated_at = get_current_vn_time()
        try:
            db.add(pl)
            db.commit()
        except Exception:
            db.rollback()
        return new_code

    @staticmethod
    def _resolve_service_item_id(db: Session, item: Any) -> Optional[Any]:
        def get_val(key_list):
            if isinstance(item, dict):
                for k in key_list:
                    if k in item and item[k]:
                        return item[k]
            else:
                for k in key_list:
                    val = getattr(item, k, None)
                    if val:
                        return val
            return None

        raw_id = get_val(["service_item_id", "serviceItemId", "id"])
        if raw_id:
            try:
                srv = db.query(ServiceItem).filter(ServiceItem.id == (uuid.UUID(str(raw_id)) if not isinstance(raw_id, uuid.UUID) else raw_id)).first()
                if srv:
                    return srv.id
            except Exception:
                pass

        code = get_val(["service_code", "serviceCode", "code"])
        if code:
            srv = db.query(ServiceItem).filter(ServiceItem.service_code == str(code).strip()).first()
            if srv:
                return srv.id

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
            func.max(PriceListVersion.created_at).label("max_created")
        ).group_by(PriceListVersion.price_list_id).subquery()

        latest = db.query(PriceListVersion).join(
            subquery,
            (PriceListVersion.price_list_id == subquery.c.price_list_id) & (PriceListVersion.created_at == subquery.c.max_created)
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
            subquery = (
                db.query(
                    PriceListVersion.price_list_id,
                    func.max(PriceListVersion.created_at).label("max_created")
                )
                .group_by(PriceListVersion.price_list_id)
                .subquery()
            )

            query = (
                db.query(PriceList, PriceListVersion)
                .join(PriceListVersion, PriceList.id == PriceListVersion.price_list_id)
                .join(
                    subquery,
                    (PriceListVersion.price_list_id == subquery.c.price_list_id) &
                    (PriceListVersion.created_at == subquery.c.max_created)
                )
            )

            if status_filter and status_filter != "Tất cả":
                query = query.filter(PriceListVersion.status.ilike(status_filter.strip()))
            if apply_type and apply_type != "Tất cả":
                query = query.filter(PriceList.scope_type.ilike(apply_type.strip()))
            if customer and customer != "Tất cả":
                query = query.filter(
                    or_(
                        PriceList.price_list_name.ilike(f"%{customer.strip()}%"),
                        PriceListVersion.price_list_name.ilike(f"%{customer.strip()}%")
                    )
                )
            if search and search.strip():
                sterm = f"%{search.strip()}%"
                query = query.filter(
                    or_(
                        PriceList.price_list_code.ilike(sterm),
                        PriceList.price_list_name.ilike(sterm),
                        PriceListVersion.price_list_name.ilike(sterm),
                        PriceList.scope_id.ilike(sterm)
                    )
                )

            total_count = query.count()
            records = query.order_by(desc(PriceListVersion.created_at)).offset((page - 1) * page_size).limit(page_size).all()

            user_ids = {
                str(getattr(pl, "created_by", None) or getattr(ver, "created_by", None)).strip() 
                for pl, ver in records 
                if (getattr(pl, "created_by", None) or getattr(ver, "created_by", None))
            }
            users_map = PriceListService._get_users_map_from_cache(db, user_ids)

            items = []
            for pl, ver in records:
                clean_code = PriceListService._ensure_valid_price_code(db, pl)

                vf, vt = getattr(ver, "valid_from", None), getattr(ver, "valid_to", None)
                s_str = vf.strftime("%d/%m/%Y") if hasattr(vf, "strftime") else ""
                e_str = vt.strftime("%d/%m/%Y") if hasattr(vt, "strftime") else ""
                eff_time = f"{s_str} - {e_str}" if s_str and e_str else (f"Từ {s_str}" if s_str else "N/A")

                at_val = getattr(pl, "updated_at", None) or getattr(ver, "created_at", None) or getattr(pl, "created_at", None)
                at_str = at_val.strftime("%d/%m/%Y %H:%M") if hasattr(at_val, "strftime") else "N/A"
                reason = getattr(ver, "rejected_reason", None) or getattr(ver, "rejection_reason", None) or ""

                cid = str(getattr(ver, "created_by", None) or getattr(pl, "created_by", None) or "").strip().lower()
                creator = users_map.get(cid, "Staff" if (re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", cid) or not cid or cid == "none") else cid)

                # ƯU TIÊN LẤY TÊN CỦA VERSION MỚI NHẤT -> NẾU RỖNG MỚI LẤY TÊN BẢNG GIÁ CHA
                version_display_name = getattr(ver, "price_list_name", None) or getattr(ver, "price_name", None) or pl.price_list_name or "N/A"

                items.append({
                    "id": clean_code,
                    "priceCode": clean_code,
                    "price_code": clean_code,
                    "versionId": str(ver.id),
                    "name": str(version_display_name),
                    "priceName": str(version_display_name),
                    "price_name": str(version_display_name),
                    "price_list_name": str(version_display_name),
                    "contractId": str(getattr(pl, "scope_id", None) or getattr(pl, "contract_id", None) or "N/A"),
                    "type": str(pl.scope_type or "GENERAL").upper(),
                    "version": format_version(getattr(ver, "version_number", "1.0")),
                    "effectiveTime": eff_time,
                    "status": str(ver.status or "DRAFT").upper(),
                    "rejectReason": str(reason),
                    "rejectionReason": str(reason),
                    "updatedBy": creator,
                    "updatedAt": at_str
                })

            customers = ["Tất cả"] + [c[0] for c in db.query(PriceList.price_list_name).filter(PriceList.price_list_name.isnot(None)).distinct().all() if c[0]]
            types = ["Tất cả", "CUSTOMER", "CONTRACT", "GENERAL", "SERVICE_GROUP", "SERVICE_TYPE"]
            
            return {
                "items": items,
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "available_types": types,
                "available_customers": customers
            }

        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Lỗi Server: {str(e)}")

    @staticmethod
    def get_detail_by_code(db: Session, price_code: str, version_id: Optional[str] = None) -> Dict[str, Any]:
        """Lấy chính xác dữ liệu dịch vụ, thời gian hiệu lực và danh sách lịch sử tất cả phiên bản."""
        conds = [PriceList.price_list_code == price_code]
        try:
            conds.append(PriceList.id == uuid.UUID(price_code))
        except ValueError:
            pass

        pl = db.query(PriceList).options(joinedload(PriceList.versions)).filter(or_(*conds)).first()
        if not pl:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy bảng giá '{price_code}'")

        ver = None
        if version_id and str(version_id).strip():
            clean_ver_str = str(version_id).strip()
            
            # 1. Thử tìm theo UUID trực tiếp
            try:
                ver_uuid = uuid.UUID(clean_ver_str)
                ver = db.query(PriceListVersion).filter(
                    PriceListVersion.price_list_id == pl.id,
                    PriceListVersion.id == ver_uuid
                ).first()
            except ValueError:
                pass

            # 2. Nếu version_id truyền lên là chuỗi như "2.1" hoặc "v2.0"
            if not ver:
                clean_target = clean_ver_str.lower().lstrip("v")
                for v in pl.versions:
                    v_num_clean = str(v.version_number or "").lower().lstrip("v")
                    if v_num_clean == clean_target:
                        ver = v
                        break

        # 3. Nếu vẫn không tìm thấy thì mới lấy phiên bản mặc định
        if not ver:
            ver = PriceListService._get_latest_version(pl)

        if not ver:
            raise HTTPException(status_code=404, detail=f"Bảng giá '{price_code}' chưa có phiên bản nào.")

        clean_code = PriceListService._ensure_valid_price_code(db, pl)

        # Trích xuất thời gian hiệu lực ĐÚNG của phiên bản `ver`
        vf, vt = getattr(ver, "valid_from", None), getattr(ver, "valid_to", None)
        vf_str = vf.strftime("%Y-%m-%d") if hasattr(vf, "strftime") and vf else ""
        vt_str = vt.strftime("%Y-%m-%d") if hasattr(vt, "strftime") and vt else ""

        # LẤY ĐÚNG DANH SÁCH DỊCH VỤ CỦA CHÍNH PHIÊN BẢN (ver.id) NÀY
        details = db.query(PriceListDetail).options(
            joinedload(PriceListDetail.service_item)
        ).filter(PriceListDetail.price_list_version_id == ver.id).all()

        services_data = []
        for item in details:
            srv = item.service_item
            services_data.append({
                "serviceItemId": str(srv.id) if srv else str(item.service_item_id),
                "service_item_id": str(srv.id) if srv else str(item.service_item_id),
                "code": srv.service_code if srv else "SRV-DEFAULT",
                "serviceCode": srv.service_code if srv else "SRV-DEFAULT",
                "service_code": srv.service_code if srv else "SRV-DEFAULT",
                "name": srv.service_name if srv else "Dịch vụ chuẩn",
                "serviceName": srv.service_name if srv else "Dịch vụ chuẩn",
                "service_name": srv.service_name if srv else "Dịch vụ chuẩn",
                "unit": srv.unit if srv else "Lượt",
                "serviceGroup": getattr(srv, "service_group", "") if srv else "",
                "service_group": getattr(srv, "service_group", "") if srv else "",
                "price": safe_float(item.unit_price),
                "unitPrice": safe_float(item.unit_price),
                "unit_price": safe_float(item.unit_price)
            })

        current_ver_status = str(ver.status or "DRAFT").upper()
        reason = getattr(ver, "rejected_reason", None) or getattr(ver, "rejection_reason", None) or ""
        scope_id = str(getattr(pl, "scope_id", None) or getattr(pl, "contract_id", None) or getattr(pl, "customer_id", None) or "")

        # Lấy tên của phiên bản con (ver), nếu rỗng mới lấy tên bảng cha (pl)
        display_name = getattr(ver, "price_list_name", None) or pl.price_list_name or "N/A"

        # TẠO DANH SÁCH TẤT CẢ PHIÊN BẢN ĐỂ HIỂN THỊ Ở CỘT BÊN TRÁI TRANG LỊCH SỬ
        versions_list = []
        # Sắp xếp phiên bản giảm dần theo created_at
        sorted_versions = sorted(
            pl.versions, 
            key=lambda v: getattr(v, "created_at", None) or datetime.min, 
            reverse=True
        )
        for v in sorted_versions:
            v_vf, v_vt = getattr(v, "valid_from", None), getattr(v, "valid_to", None)
            v_vf_str = v_vf.strftime("%Y-%m-%d") if hasattr(v_vf, "strftime") and v_vf else ""
            v_vt_str = v_vt.strftime("%Y-%m-%d") if hasattr(v_vt, "strftime") and v_vt else ""
            v_name = getattr(v, "price_list_name", None) or pl.price_list_name or "N/A"

            versions_list.append({
                "id": str(v.id),
                "versionId": str(v.id),
                "version": format_version(getattr(v, "version_number", "1.0")),
                "versionNumber": getattr(v, "version_number", "1.0"),
                "priceName": v_name,
                "price_name": v_name,
                "status": str(v.status or "DRAFT").upper(),
                "validFrom": v_vf_str,
                "validTo": v_vt_str,
                "effectiveFrom": v_vf_str,
                "effectiveTo": v_vt_str,
            })

        return {
            "id": clean_code,
            "priceCode": clean_code,
            "price_code": clean_code,
            "versionId": str(ver.id),
            "priceName": display_name,
            "price_name": display_name,
            "scopeType": str(pl.scope_type or "CUSTOMER"),
            "scope_type": str(pl.scope_type or "CUSTOMER"),
            "targetType": str(pl.scope_type or "CUSTOMER"),
            "target_type": str(pl.scope_type or "CUSTOMER"),
            "scopeId": scope_id or "N/A",
            "scope_id": scope_id or "N/A",
            "specificTarget": scope_id,
            "specific_target": scope_id,
            "version": format_version(getattr(ver, "version_number", "1.0")),
            "status": current_ver_status,
            "rejectReason": reason,
            "rejectionReason": reason,
            "validFrom": vf_str,
            "validTo": vt_str,
            "effectiveFrom": vf_str,
            "effective_from": vf_str,
            "effectiveTo": vt_str,
            "effective_to": vt_str,
            "services": services_data,
            "items": services_data,
            "versions": versions_list  # Bổ sung danh sách các phiên bản cho trang Lịch sử
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
            user_id = current_user.id if current_user else None
            user_uuid = uuid.UUID(str(user_id)) if user_id else None
            now = get_current_vn_time()
            scope_id_val = payload.specific_target.strip() if (payload.target_type != "GENERAL" and payload.specific_target) else None

            new_price_list = PriceList(
                id=uuid.uuid4(),
                price_list_code=price_code,
                price_list_name=payload.price_name,
                scope_type=payload.target_type,
                scope_id=scope_id_val,
                created_at=now,
                updated_at=now,
                created_by=user_uuid
            )
            db.add(new_price_list)
            db.flush()

            stage_val = "MANAGER_PENDING" if status_upper == "SUBMITTED" else "DRAFT"
            new_version = PriceListVersion(
                id=uuid.uuid4(),
                price_list_id=new_price_list.id,
                version_number="1.0",
                status=status_upper,
                approval_stage=stage_val,
                valid_from=payload.effective_from,
                valid_to=payload.effective_to,
                created_at=now,
                created_by=user_uuid
            )
            db.add(new_version)
            db.flush()

            for item in payload.services:
                target_service_id = PriceListService._resolve_service_item_id(db, item)
                if not target_service_id:
                    continue

                if isinstance(item, dict):
                    price_raw = item.get("price", item.get("unit_price", item.get("unitPrice", 0.0)))
                else:
                    price_raw = getattr(item, "price", getattr(item, "unit_price", getattr(item, "unitPrice", 0.0)))

                detail = PriceListDetail(
                    id=uuid.uuid4(),
                    price_list_id=new_price_list.id,
                    price_list_version_id=new_version.id,
                    service_item_id=target_service_id,
                    unit_price=safe_float(price_raw)
                )
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
    def update_price_list(
        db: Session, 
        price_code: str, 
        payload: PriceListCreate, 
        current_user: Optional[CurrentUser] = None
    ) -> Dict[str, Any]:
        # 1. Tìm PriceList theo Code hoặc UUID
        conds = [PriceList.price_list_code == price_code]
        try:
            conds.append(PriceList.id == uuid.UUID(price_code))
        except ValueError:
            pass

        pl = db.query(PriceList).options(joinedload(PriceList.versions)).filter(or_(*conds)).first()
        if not pl:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy bảng giá '{price_code}'")

        # 2. Ưu tiên lấy theo version_id gửi từ Payload (nếu có), nếu không mới lấy phiên bản mới nhất
        payload_version_id = getattr(payload, "version_id", None)
        if payload_version_id:
            try:
                target_ver_uuid = uuid.UUID(str(payload_version_id))
                ver = db.query(PriceListVersion).filter(
                    PriceListVersion.id == target_ver_uuid,
                    PriceListVersion.price_list_id == pl.id
                ).first()
            except ValueError:
                ver = None
        else:
            ver = PriceListService._get_latest_version(pl)

        if not ver:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy phiên bản phù hợp của bảng giá '{price_code}'.")

        current_status = str(ver.status or "").upper()
        if current_status not in ["DRAFT", "REJECTED"]:
            raise HTTPException(status_code=400, detail=f"Không thể chỉnh sửa bảng giá ở trạng thái '{current_status}'.")

        target_status = payload.status.upper() if payload.status else current_status

        # 3. Kiểm tra trùng lặp thời gian hiệu lực
        if target_status != "DRAFT":
            PriceListService._validate_overlapping_time(
                db=db,
                scope_type=payload.target_type,
                scope_id=payload.specific_target,
                effective_from=payload.effective_from,
                effective_to=payload.effective_to,
                exclude_price_list_id=pl.id
            )

        try:
            user_id = current_user.id if current_user else None
            user_uuid = uuid.UUID(str(user_id)) if user_id else None
            now = get_current_vn_time()

            pl.updated_at = now
            clean_code = PriceListService._ensure_valid_price_code(db, pl)

            # 4. Phân nhánh xử lý theo trạng thái hiện tại
            if current_status == "REJECTED":
                # Nếu bị Từ chối -> Sinh phiên bản mới
                new_ver_num = PriceListService._generate_next_version_number(ver.version_number)
                stage_val = "MANAGER_PENDING" if target_status == "SUBMITTED" else "DRAFT"

                target_version = PriceListVersion(
                    id=uuid.uuid4(),
                    price_list_id=pl.id,
                    version_number=new_ver_num,
                    status=target_status,
                    approval_stage=stage_val,
                    valid_from=payload.effective_from,
                    valid_to=payload.effective_to,
                    parent_version_id=ver.id,
                    created_by=user_uuid,
                    created_at=now
                )
                # Đồng bộ tên bảng giá vào phiên bản mới
                if hasattr(target_version, "price_list_name"):
                    target_version.price_list_name = payload.price_name

                db.add(target_version)
                db.flush()
                old_service_map = {}
            else:
                # Cập nhật trực tiếp trên phiên bản DRAFT
                target_version = ver

                # Ghi log cập nhật tên bảng giá
                if pl.price_list_name != payload.price_name:
                    db.add(PriceChangeHistory(
                        id=uuid.uuid4(),
                        price_list_version_id=target_version.id,
                        entity_type="PRICE_LIST",
                        entity_name=pl.price_list_code,
                        field_name="price_list_name",
                        old_value=str(pl.price_list_name or ""),
                        new_value=str(payload.price_name or ""),
                        change_reason="Thay đổi tên bảng giá",
                        changed_by=user_uuid,
                        changed_at=now
                    ))
                    pl.price_list_name = payload.price_name

                    # Cập nhật tên vào phiên bản hiện tại
                    if hasattr(target_version, "price_list_name"):
                        target_version.price_list_name = payload.price_name

                # Ghi log thời gian bắt đầu
                old_vf_str = target_version.valid_from.strftime("%d/%m/%Y") if target_version.valid_from else ""
                new_vf_str = payload.effective_from.strftime("%d/%m/%Y") if payload.effective_from else ""
                if old_vf_str != new_vf_str:
                    db.add(PriceChangeHistory(
                        id=uuid.uuid4(),
                        price_list_version_id=target_version.id,
                        entity_type="PRICE_LIST",
                        entity_name=pl.price_list_code,
                        field_name="valid_from",
                        old_value=old_vf_str,
                        new_value=new_vf_str,
                        change_reason="Thay đổi thời gian bắt đầu hiệu lực",
                        changed_by=user_uuid,
                        changed_at=now
                    ))
                    target_version.valid_from = payload.effective_from

                # Ghi log thời gian kết thúc
                old_vt_str = target_version.valid_to.strftime("%d/%m/%Y") if target_version.valid_to else ""
                new_vt_str = payload.effective_to.strftime("%d/%m/%Y") if payload.effective_to else ""
                if old_vt_str != new_vt_str:
                    db.add(PriceChangeHistory(
                        id=uuid.uuid4(),
                        price_list_version_id=target_version.id,
                        entity_type="PRICE_LIST",
                        entity_name=pl.price_list_code,
                        field_name="valid_to",
                        old_value=old_vt_str,
                        new_value=new_vt_str,
                        change_reason="Thay đổi thời gian kết thúc hiệu lực",
                        changed_by=user_uuid,
                        changed_at=now
                    ))
                    target_version.valid_to = payload.effective_to

                target_version.status = target_status
                if target_status == "SUBMITTED":
                    target_version.approval_stage = "MANAGER_PENDING"

                # Đọc danh sách dịch vụ cũ trước khi xóa
                old_details = db.query(PriceListDetail).filter(
                    PriceListDetail.price_list_version_id == target_version.id
                ).all()
                old_service_map = {dt.service_item_id: dt.unit_price for dt in old_details}

                # Xóa chi tiết cũ để ghi nhận chi tiết mới
                db.query(PriceListDetail).filter(
                    PriceListDetail.price_list_version_id == target_version.id
                ).delete(synchronize_session=False)

            # 5. Lưu danh sách Dịch vụ mới & Ghi Log
            new_service_ids = set()

            for item in payload.services:
                target_service_id = PriceListService._resolve_service_item_id(db, item)
                if not target_service_id:
                    continue

                new_service_ids.add(target_service_id)

                if isinstance(item, dict):
                    price_raw = item.get("price", item.get("unit_price", item.get("unitPrice", 0.0)))
                else:
                    price_raw = getattr(item, "price", getattr(item, "unit_price", getattr(item, "unitPrice", 0.0)))

                new_price = safe_float(price_raw)

                detail = PriceListDetail(
                    id=uuid.uuid4(),
                    price_list_id=pl.id,
                    price_list_version_id=target_version.id,
                    service_item_id=target_service_id,
                    unit_price=new_price
                )
                db.add(detail)

                if current_status != "REJECTED":
                    srv_obj = db.query(ServiceItem).filter(ServiceItem.id == target_service_id).first()
                    srv_name = srv_obj.service_name if srv_obj else "Dịch vụ"

                    if target_service_id not in old_service_map:
                        db.add(PriceChangeHistory(
                            id=uuid.uuid4(),
                            price_list_version_id=target_version.id,
                            entity_type="SERVICE_ITEM",
                            entity_name=srv_name,
                            field_name="unit_price",
                            old_value=None,
                            new_value=str(new_price),
                            change_reason="Thêm dịch vụ vào bảng giá",
                            changed_by=user_uuid,
                            changed_at=now
                        ))
                    elif safe_float(old_service_map[target_service_id]) != new_price:
                        db.add(PriceChangeHistory(
                            id=uuid.uuid4(),
                            price_list_version_id=target_version.id,
                            entity_type="SERVICE_ITEM",
                            entity_name=srv_name,
                            field_name="unit_price",
                            old_value=str(safe_float(old_service_map[target_service_id])),
                            new_value=str(new_price),
                            change_reason="Thay đổi đơn giá dịch vụ",
                            changed_by=user_uuid,
                            changed_at=now
                        ))

            # 6. Ghi Log dịch vụ bị loại bỏ
            if current_status != "REJECTED":
                for old_srv_id, old_price in old_service_map.items():
                    if old_srv_id not in new_service_ids:
                        srv_obj = db.query(ServiceItem).filter(ServiceItem.id == old_srv_id).first()
                        srv_name = srv_obj.service_name if srv_obj else "Dịch vụ"

                        db.add(PriceChangeHistory(
                            id=uuid.uuid4(),
                            price_list_version_id=target_version.id,
                            entity_type="SERVICE_ITEM",
                            entity_name=srv_name,
                            field_name="unit_price",
                            old_value=str(safe_float(old_price)),
                            new_value=None,
                            change_reason="Xóa dịch vụ khỏi bảng giá",
                            changed_by=user_uuid,
                            changed_at=now
                        ))

            db.commit()
            return {
                "id": clean_code, 
                "priceCode": clean_code, 
                "version": format_version(target_version.version_number),
                "versionId": str(target_version.id),
                "message": f"Cập nhật thành công phiên bản {format_version(target_version.version_number)}"
            }

        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Lỗi khi cập nhật bảng giá: {str(e)}")


    @staticmethod
    def approve_or_reject_price_list(
        db: Session,
        version_id: str,
        action: str,
        reject_reason: Optional[str] = None,
        current_user: Optional[CurrentUser] = None
    ) -> Dict[str, Any]:
        """API cho Cấp quản lý/Giám đốc duyệt hoặc từ chối phiên bản hiện tại"""
        try:
            ver = db.query(PriceListVersion).filter(PriceListVersion.id == uuid.UUID(version_id)).first()
        except ValueError:
            ver = None

        if not ver:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên bản bảng giá này.")

        action_upper = action.upper()
        if action_upper == "REJECT":
            if not reject_reason or not reject_reason.strip():
                raise HTTPException(status_code=400, detail="Vui lòng nhập lý do từ chối.")
            
            ver.status = "REJECTED"
            ver.approval_stage = "REJECTED"
            if hasattr(ver, "rejected_reason"):
                ver.rejected_reason = reject_reason.strip()
            if hasattr(ver, "rejection_reason"):
                ver.rejection_reason = reject_reason.strip()

        elif action_upper == "APPROVE":
            ver.status = "APPROVED"
            ver.approval_stage = "APPROVED"
            if hasattr(ver, "rejected_reason"):
                ver.rejected_reason = None
            if hasattr(ver, "rejection_reason"):
                ver.rejection_reason = None

        if hasattr(ver, "updated_at"):
            ver.updated_at = get_current_vn_time()

        db.commit()

        return {"message": f"Đã {action_upper} thành công phiên bản {format_version(ver.version_number)}"}

    @staticmethod
    def delete_service_item(
        db: Session, 
        price_code: str, 
        service_identifier: str, 
        current_user: Optional[CurrentUser] = None
    ) -> Dict[str, Any]:
        conds = [PriceList.price_list_code == price_code]
        try:
            conds.append(PriceList.id == uuid.UUID(price_code))
        except ValueError:
            pass

        pl = db.query(PriceList).options(joinedload(PriceList.versions)).filter(or_(*conds)).first()
        if not pl:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy bảng giá '{price_code}'")

        ver = PriceListService._get_latest_version(pl)
        if not ver:
            raise HTTPException(status_code=404, detail=f"Bảng giá '{price_code}' chưa có phiên bản nào.")

        current_status = str(ver.status or "").upper()
        if current_status not in ["DRAFT", "REJECTED"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Không thể xóa dịch vụ ở bảng giá có trạng thái '{current_status}'."
            )

        try:
            srv_conds = [ServiceItem.service_code == service_identifier]
            try:
                srv_conds.append(ServiceItem.id == uuid.UUID(service_identifier))
            except ValueError:
                pass

            service_item = db.query(ServiceItem).filter(or_(*srv_conds)).first()
            if not service_item:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Không tìm thấy dịch vụ có mã/ID '{service_identifier}' trong hệ thống."
                )

            detail_item = db.query(PriceListDetail).filter(
                PriceListDetail.price_list_version_id == ver.id,
                PriceListDetail.service_item_id == service_item.id
            ).first()

            if not detail_item:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Dịch vụ '{service_item.service_code}' không tồn tại trong phiên bản bảng giá này."
                )

            user_id = current_user.id if current_user else None
            user_uuid = uuid.UUID(str(user_id)) if user_id else None
            now = get_current_vn_time()

            log = PriceChangeHistory(
                id=uuid.uuid4(),
                price_list_version_id=ver.id,
                entity_type="SERVICE_ITEM",
                entity_name=service_item.service_name,
                field_name="unit_price",
                old_value=str(detail_item.unit_price),
                new_value=None,
                change_reason="Xóa dịch vụ khỏi bảng giá",
                changed_by=user_uuid,
                changed_at=now
            )
            db.add(log)

            db.delete(detail_item)
            pl.updated_at = now
            db.commit()

            return {"message": f"Xóa dịch vụ '{service_item.service_code}' khỏi bảng giá thành công."}

        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Lỗi khi xóa dịch vụ: {str(e)}")

    @staticmethod
    def auto_expire_versions(db: Session) -> int:
        """Tự động chuyển các bản ghi EFFECTIVE đã qua ngày valid_to sang EXPIRED"""
        today = get_current_vn_time().date()
        expired_versions = db.query(PriceListVersion).filter(
            PriceListVersion.status == "EFFECTIVE",
            PriceListVersion.valid_to.isnot(None),
            PriceListVersion.valid_to < today
        ).all()

        for ver in expired_versions:
            ver.status = "EXPIRED"

        if expired_versions:
            db.commit()

        return len(expired_versions)

    
    @staticmethod
    def create_new_version(
        db: Session,
        price_code: str,
        payload: Any = None,
        valid_from: Optional[Union[datetime, str]] = None,
        valid_to: Optional[Union[datetime, str]] = None,
        services: Optional[List[Dict[str, Any]]] = None,
        current_user: Optional[Any] = None,
        price_list_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Tạo phiên bản mới (SUBMITTED) từ phiên bản EFFECTIVE hiện tại."""
        
        # 1. Tìm Bảng giá gốc (PriceList)
        conds = [PriceList.price_list_code == price_code]
        try:
            conds.append(PriceList.id == uuid.UUID(price_code))
        except ValueError:
            pass

        pl = db.query(PriceList).options(joinedload(PriceList.versions)).filter(or_(*conds)).first()
        if not pl:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy bảng giá '{price_code}'")

        # 2. Lấy phiên bản EFFECTIVE hiện tại
        current_ver = PriceListService._get_latest_version(pl)
        if not current_ver:
            raise HTTPException(status_code=404, detail=f"Bảng giá '{price_code}' chưa có phiên bản nào.")

        if str(current_ver.status or "").upper() != "EFFECTIVE":
            raise HTTPException(
                status_code=400,
                detail=f"Chỉ có thể tạo phiên bản mới từ phiên bản đang 'EFFECTIVE'. Trạng thái hiện tại: '{current_ver.status}'"
            )

        try:
            now = get_current_vn_time()
            user_id = current_user.id if current_user else None
            user_uuid = uuid.UUID(str(user_id)) if user_id and str(user_id) != "None" else None

            # --- BẮT DỮ LIỆU TỪ PAYLOAD FRONTEND ---
            raw_data = payload
            if hasattr(payload, "dict"):
                raw_data = payload.dict(by_alias=True)
            elif hasattr(payload, "__dict__"):
                raw_data = payload.__dict__

            inner_data = {}
            if isinstance(raw_data, dict):
                inner_data = raw_data.get("data", raw_data) if isinstance(raw_data.get("data"), dict) else raw_data

            # 1. Bắt tên mới dành riêng cho Phiên bản mới
            extracted_new_name = (
                price_list_name or
                (getattr(payload, "price_name", None) if payload else None) or
                (getattr(payload, "price_list_name", None) if payload else None) or
                (getattr(payload, "priceName", None) if payload else None) or
                inner_data.get("priceName") or
                inner_data.get("price_name") or
                inner_data.get("price_list_name") or
                inner_data.get("currentPriceName") or
                inner_data.get("name")
            )

            # Lấy tên cũ của version trước làm fallback nếu FE không truyền tên mới
            current_ver_name = getattr(current_ver, 'price_list_name', None) or getattr(current_ver, 'price_name', None) or pl.price_list_name

            # Nếu Frontend gửi tên mới thì dùng tên mới cho VERSION MỚI, ngược lại mới dùng lại tên cũ
            new_version_name = str(extracted_new_name).strip() if extracted_new_name and str(extracted_new_name).strip() else current_ver_name

            # GIỮ NGUYÊN pl.price_list_name (Không update bảng PriceList cha để bảo toàn tên gốc)

            valid_from = valid_from or inner_data.get("valid_from") or inner_data.get("effective_from") or inner_data.get("validFrom") or inner_data.get("effectiveFrom")
            valid_to = valid_to or inner_data.get("valid_to") or inner_data.get("effective_to") or inner_data.get("validTo") or inner_data.get("effectiveTo")
            
            if services is None:
                services = (
                    inner_data.get("services") or 
                    inner_data.get("service_items") or 
                    inner_data.get("serviceItems") or 
                    inner_data.get("items") or 
                    inner_data.get("details") or 
                    inner_data.get("price_list_details")
                )

            def safe_parse_date(dt_val):
                if not dt_val:
                    return None
                if isinstance(dt_val, datetime):
                    return dt_val
                try:
                    return parse_date(str(dt_val))
                except Exception:
                    return None

            parsed_valid_from = safe_parse_date(valid_from) or now
            parsed_valid_to = safe_parse_date(valid_to)

            # 3. Sinh số phiên bản mới
            raw_next_ver = PriceListService._generate_next_version_number(current_ver.version_number)
            clean_ver_str = str(raw_next_ver).lstrip("vV")
            formatted_version = f"v{clean_ver_str}"

            # Cập nhật thời hạn của phiên bản EFFECTIVE cũ
            current_ver.valid_to = parsed_valid_from

            # 4. CHỈ LƯU TÊN MỚI VÀO PHIÊN BẢN MỚI NÀY
            new_ver = PriceListVersion(
                id=uuid.uuid4(),
                price_list_id=pl.id,
                price_list_name=new_version_name,  # Tên mới gán riêng biệt tại bản ghi version này
                version_number=formatted_version,
                status="SUBMITTED",
                approval_stage="MANAGER_PENDING",
                valid_from=parsed_valid_from,
                valid_to=parsed_valid_to,
                parent_version_id=current_ver.id,
                created_by=user_uuid,
                created_at=now
            )

            db.add(new_ver)
            db.flush()

            # 5. LƯU DỊCH VỤ VÀO BẢNG price_list_detail
            if services is not None and isinstance(services, list):
                for item in services:
                    target_service_id = PriceListService._resolve_service_item_id(db, item)
                    
                    if not target_service_id and isinstance(item, dict):
                        raw_id = item.get("service_item_id") or item.get("service_id") or item.get("id") or item.get("serviceItemId")
                        if raw_id:
                            try:
                                target_service_id = uuid.UUID(str(raw_id))
                            except ValueError:
                                pass
                    
                    if not target_service_id:
                        continue

                    if isinstance(item, dict):
                        price_raw = item.get("unit_price", item.get("unitPrice", item.get("price", 0.0)))
                    else:
                        price_raw = getattr(item, "unit_price", getattr(item, "unitPrice", getattr(item, "price", 0.0)))

                    new_price = safe_float(price_raw)

                    detail = PriceListDetail(
                        id=uuid.uuid4(),
                        price_list_id=pl.id,
                        price_list_version_id=new_ver.id,
                        service_item_id=target_service_id,
                        unit_price=new_price
                    )
                    db.add(detail)
            else:
                old_details = db.query(PriceListDetail).filter(
                    PriceListDetail.price_list_version_id == current_ver.id
                ).all()

                for dt in old_details:
                    new_dt = PriceListDetail(
                        id=uuid.uuid4(),
                        price_list_id=pl.id,
                        price_list_version_id=new_ver.id,
                        service_item_id=dt.service_item_id,
                        unit_price=dt.unit_price
                    )
                    db.add(new_dt)

            pl.updated_at = now
            db.commit()

            # Trả về Response chứa đúng tên của phiên bản mới
            return {
                "id": str(pl.id),
                "priceCode": pl.price_list_code,
                "priceName": new_version_name,
                "price_list_name": new_version_name,
                "price_name": new_version_name,
                "versionId": str(new_ver.id),
                "version": formatted_version,
                "validFrom": new_ver.valid_from.isoformat() if new_ver.valid_from else None,
                "validTo": new_ver.valid_to.isoformat() if new_ver.valid_to else None,
                "message": f"Tạo thành công phiên bản mới {formatted_version} và đã gửi phê duyệt."
            }

        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Lỗi khi tạo phiên bản mới: {str(e)}")