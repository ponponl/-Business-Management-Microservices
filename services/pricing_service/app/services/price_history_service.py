import re
from typing import List, Dict, Set, Optional
from uuid import UUID
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.pricing import (
    PriceList,
    PriceListVersion,
    PriceListDetail,
    ServiceItem,
    PriceChangeHistory,
    PriceListUsageLog,
    UserCache,
)
from app.schemas.price_history import (
    VersionHistoryItem,
    VersionDetailResponse,
    PriceDetailItem,
    ChangeHistoryItem,
    UsageLogItem,
    VersionCompareHeader,
    PriceComparisonItem,
    VersionComparisonResponse,
)


class PriceHistoryService:

    @staticmethod
    def _get_users_map(db: Session, user_ids: Set[str]) -> Dict[str, str]:
        """Hàm hỗ trợ lấy danh sách tên hiển thị của User từ Cache một cách an toàn."""
        if not user_ids:
            return {}
        clean_ids = [str(uid).strip().lower() for uid in user_ids if uid]
        try:
            cached = db.query(UserCache).filter(func.lower(UserCache.user_id).in_(clean_ids)).all()
            return {
                str(u.user_id).strip().lower(): (
                    getattr(u, "full_name", None) or getattr(u, "username", None) or str(u.user_id)
                )
                for u in cached
            }
        except Exception:
            return {}

    @staticmethod
    def log_price_usage(
        db: Session,
        price_list_version_id: UUID,
        payment_board_id: Optional[UUID] = None,
        payment_code: Optional[str] = None,
        status_str: str = "CALCULATED",
        total_amount: Optional[float] = None,
        customer_id: Optional[UUID] = None,
        contract_id: Optional[UUID] = None,
        service_item_id: Optional[UUID] = None,
        issued_by: Optional[str] = None,
        applied_at: Optional[datetime] = None,
    ) -> PriceListUsageLog:
        """
        Hàm ghi nhật ký áp dụng bảng giá vào CSDL.
        Gọi hàm này từ Payment Service / Consumer Kafka khi một bản kê hoặc hóa đơn áp dụng bảng giá.
        """
        version = db.query(PriceListVersion).filter(PriceListVersion.id == price_list_version_id).first()
        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy phiên bản bảng giá với ID: {price_list_version_id}"
            )

        usage_log = PriceListUsageLog(
            price_list_id=version.price_list_id,
            price_list_version_id=version.id,
            payment_board_id=payment_board_id,
            payment_code=payment_code,
            status=status_str,
            total_amount=total_amount,
            customer_id=customer_id,
            contract_id=contract_id,
            service_item_id=service_item_id,
            issued_by=issued_by,
            applied_at=applied_at or datetime.utcnow(),
        )

        db.add(usage_log)
        db.commit()
        db.refresh(usage_log)
        return usage_log

    @staticmethod
    def get_version_history_list(
        db: Session, 
        price_list_identifier: str  
    ) -> List[VersionHistoryItem]:
        """Lấy danh sách các phiên bản theo mã Bảng giá hoặc ID Bảng giá."""
        
        price_list = (
            db.query(PriceList)
            .filter(PriceList.price_list_code == price_list_identifier)
            .first()
        )

        if not price_list:
            try:
                uuid_obj = UUID(price_list_identifier)
                price_list = (
                    db.query(PriceList)
                    .filter(PriceList.id == uuid_obj)
                    .first()
                )
            except ValueError:
                pass

        if not price_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Không tìm thấy bảng giá với mã hoặc ID: {price_list_identifier}"
            )

        versions = (
            db.query(PriceListVersion)
            .filter(PriceListVersion.price_list_id == price_list.id)
            .order_by(PriceListVersion.created_at.desc())
            .all()
        )

        result = []
        for v in versions:
            v_name = (
                getattr(v, "price_list_name", None) or 
                getattr(v, "price_name", None) or 
                price_list.price_list_name
            )
            
            result.append(
                VersionHistoryItem(
                    id=v.id,
                    version_number=v.version_number,
                    status=v.status,
                    price_list_name=v_name,  
                    valid_from=v.valid_from,
                    valid_to=v.valid_to,
                )
            )

        return result

    @staticmethod
    def get_version_details(db: Session, version_id: UUID) -> VersionDetailResponse:
        """Tab 1: Thông tin chung bảng giá & Cấu hình đơn giá chi tiết của phiên bản."""
        version = db.query(PriceListVersion).filter(PriceListVersion.id == version_id).first()
        if not version:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phiên bản không tồn tại.")

        price_list = db.query(PriceList).filter(PriceList.id == version.price_list_id).first()
        if not price_list:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bảng giá chứa phiên bản này không tồn tại.")

        current_version_name = (
            getattr(version, "price_list_name", None) or 
            getattr(version, "price_name", None) or 
            price_list.price_list_name
        )

        details = (
            db.query(PriceListDetail, ServiceItem)
            .join(ServiceItem, ServiceItem.id == PriceListDetail.service_item_id)
            .filter(PriceListDetail.price_list_version_id == version_id)
            .all()
        )

        items = [
            PriceDetailItem(
                service_item_id=srv.id,
                service_code=srv.service_code,
                service_name=srv.service_name,
                unit=srv.unit,
                unit_price=float(dt.unit_price or 0.0),
            )
            for dt, srv in details
        ]

        return VersionDetailResponse(
            price_list_id=price_list.id,
            price_list_code=price_list.price_list_code,
            price_list_name=current_version_name,  
            scope_type=price_list.scope_type,
            scope_id=price_list.scope_id,
            version_id=version.id,
            version_number=version.version_number,
            status=version.status,
            valid_from=version.valid_from,
            valid_to=version.valid_to,
            items=items,
        )

    @staticmethod
    def get_change_logs(db: Session, version_id: UUID) -> List[ChangeHistoryItem]:
        """Tab 2: Nhật ký thay đổi của phiên bản (Lấy tên hiển thị từ UserCache)."""
        logs = (
            db.query(PriceChangeHistory)
            .filter(PriceChangeHistory.price_list_version_id == version_id)
            .order_by(PriceChangeHistory.changed_at.desc())
            .all()
        )

        user_ids = {str(log.changed_by).strip() for log in logs if log.changed_by}
        users_map = PriceHistoryService._get_users_map(db, user_ids)

        result = []
        for log in logs:
            cid = str(log.changed_by or "").strip().lower()
            name_from_cache = users_map.get(cid)
            
            if name_from_cache:
                display_name = name_from_cache
            elif re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", cid) or not cid:
                display_name = "Hệ thống"
            else:
                display_name = str(log.changed_by)

            result.append(
                ChangeHistoryItem(
                    id=log.id,
                    entity_type=log.entity_type,
                    entity_name=log.entity_name,
                    field_name=log.field_name,
                    old_value=log.old_value,
                    new_value=log.new_value,
                    change_reason=log.change_reason,
                    changed_by=log.changed_by,
                    changed_by_name=display_name,
                    changed_at=log.changed_at,
                )
            )

        return result

    @staticmethod
    def get_usage_logs(db: Session, version_id: UUID) -> List[UsageLogItem]:
        """Tab 3: Lịch sử áp dụng của phiên bản (Tối ưu truy vấn không bị mất dữ liệu khi service_item_id bị NULL)."""
        
        # 1. Truy vấn trực tiếp nhật ký áp dụng theo version_id
        logs = (
            db.query(PriceListUsageLog)
            .filter(PriceListUsageLog.price_list_version_id == version_id)
            .order_by(PriceListUsageLog.applied_at.desc())
            .all()
        )

        # 2. Fallback: Nếu không tìm thấy theo version_id, thử tra cứu theo price_list_id
        if not logs:
            version = db.query(PriceListVersion).filter(PriceListVersion.id == version_id).first()
            if version:
                logs = (
                    db.query(PriceListUsageLog)
                    .filter(PriceListUsageLog.price_list_id == version.price_list_id)
                    .order_by(PriceListUsageLog.applied_at.desc())
                    .all()
                )

        if not logs:
            return []

        # 3. Lấy tên hiển thị của người thực hiện từ UserCache
        user_ids = {str(log.issued_by).strip() for log in logs if log.issued_by}
        users_map = PriceHistoryService._get_users_map(db, user_ids)

        # 4. Map thông tin ServiceItem nếu có service_item_id
        service_ids = {log.service_item_id for log in logs if getattr(log, "service_item_id", None)}
        services_map = {}
        if service_ids:
            services = db.query(ServiceItem).filter(ServiceItem.id.in_(service_ids)).all()
            services_map = {srv.id: srv for srv in services}

        result = []
        for log in logs:
            issued_by_id = str(log.issued_by or "").strip().lower()
            name_from_cache = users_map.get(issued_by_id)
            
            if name_from_cache:
                issued_by_name = name_from_cache
            elif re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", issued_by_id) or not issued_by_id:
                issued_by_name = "Hệ thống"
            else:
                issued_by_name = str(log.issued_by)

            srv = services_map.get(getattr(log, "service_item_id", None))

            result.append(
                UsageLogItem(
                    id=log.id,
                    payment_board_id=getattr(log, "payment_board_id", None),
                    payment_code=getattr(log, "payment_code", None),
                    status=getattr(log, "status", "CALCULATED"),
                    total_amount=float(log.total_amount) if getattr(log, "total_amount", None) is not None else None,
                    customer_id=getattr(log, "customer_id", None),
                    contract_id=getattr(log, "contract_id", None),
                    issued_by=log.issued_by,
                    issued_by_name=issued_by_name,
                    service_item_id=srv.id if srv else None,
                    service_code=srv.service_code if srv else None,
                    service_name=srv.service_name if srv else None,
                    applied_at=log.applied_at,
                )
            )

        return result

    @staticmethod
    def compare_versions(
        db: Session, 
        source_version_id: UUID, 
        target_version_id: UUID
    ) -> VersionComparisonResponse:
        """So sánh chênh lệch đơn giá giữa 2 phiên bản (Ví dụ: v3.0 Cũ vs v3.1 Mới)."""
        source_ver = db.query(PriceListVersion).filter(PriceListVersion.id == source_version_id).first()
        target_ver = db.query(PriceListVersion).filter(PriceListVersion.id == target_version_id).first()

        if not source_ver or not target_ver:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Một trong hai phiên bản không tồn tại."
            )

        # 1. Truy vấn danh sách chi tiết đơn giá kèm thông tin Dịch vụ của cả 2 phiên bản
        source_details = (
            db.query(PriceListDetail, ServiceItem)
            .join(ServiceItem, PriceListDetail.service_item_id == ServiceItem.id)
            .filter(PriceListDetail.price_list_version_id == source_version_id)
            .all()
        )

        target_details = (
            db.query(PriceListDetail, ServiceItem)
            .join(ServiceItem, PriceListDetail.service_item_id == ServiceItem.id)
            .filter(PriceListDetail.price_list_version_id == target_version_id)
            .all()
        )

        # 2. Gom nhóm thông tin đơn giá theo từng service_item_id
        services_map: Dict[UUID, dict] = {}

        for detail, service in source_details:
            services_map[service.id] = {
                "service_code": service.service_code,
                "service_name": service.service_name,
                "unit": service.unit,
                "old_price": float(detail.unit_price or 0.0),
                "new_price": None
            }

        for detail, service in target_details:
            if service.id in services_map:
                services_map[service.id]["new_price"] = float(detail.unit_price or 0.0)
            else:
                services_map[service.id] = {
                    "service_code": service.service_code,
                    "service_name": service.service_name,
                    "unit": service.unit,
                    "old_price": None,
                    "new_price": float(detail.unit_price or 0.0)
                }

        # 3. Tính toán chênh lệch số tiền, % chênh lệch và trạng thái
        comparison_items: List[PriceComparisonItem] = []

        for service_id, data in services_map.items():
            old_p = data["old_price"]
            new_p = data["new_price"]
            diff = None
            pct = None
            item_status = "UNCHANGED"

            if old_p is not None and new_p is not None:
                diff = round(new_p - old_p, 2)
                if old_p > 0:
                    pct = round((diff / old_p) * 100, 2)
                
                if diff > 0:
                    item_status = "INCREASED"
                elif diff < 0:
                    item_status = "DECREASED"
                else:
                    item_status = "UNCHANGED"
            elif old_p is None and new_p is not None:
                item_status = "ADDED"
            elif old_p is not None and new_p is None:
                item_status = "REMOVED"

            comparison_items.append(
                PriceComparisonItem(
                    service_item_id=service_id,
                    service_code=data["service_code"],
                    service_name=data["service_name"],
                    unit=data["unit"],
                    old_price=old_p,
                    new_price=new_p,
                    price_difference=diff,
                    percentage_change=pct,
                    status=item_status
                )
            )

        # Lấy tên bảng giá hiển thị
        price_list_name = (
            getattr(target_ver, "price_list_name", None) or 
            getattr(source_ver, "price_list_name", None) or 
            (source_ver.price_list.price_list_name if source_ver.price_list else "")
        )

        return VersionComparisonResponse(
            price_list_id=source_ver.price_list_id,
            price_list_name=price_list_name,
            source_version=VersionCompareHeader.model_validate(source_ver),
            target_version=VersionCompareHeader.model_validate(target_ver),
            comparison_items=comparison_items
        )