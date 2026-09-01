import re
from typing import List, Dict, Set
from uuid import UUID
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
                str(u.user_id).strip().lower(): (getattr(u, "full_name", None) or getattr(u, "username", None) or str(u.user_id))
                for u in cached
            }
        except Exception:
            return {}

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

        # LẤY TÊN TỪ BẢN GHI VERSION TRƯỚC (ƯU TIÊN TÊN RIÊNG CỦA VERSION NÀY)
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
            
            # Fallback hiển thị tên hợp lý
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
        """Tab 3: Lịch sử áp dụng của phiên bản (khớp payment_board_id với Payment Service)."""
        logs = (
            db.query(PriceListUsageLog, ServiceItem)
            .outerjoin(ServiceItem, ServiceItem.id == PriceListUsageLog.service_item_id)
            .filter(PriceListUsageLog.price_list_version_id == version_id)
            .order_by(PriceListUsageLog.applied_at.desc())
            .all()
        )

        return [
            UsageLogItem(
                id=log.id,
                payment_board_id=str(log.payment_board_id),
                service_item_id=srv.id if srv else None,
                service_code=srv.service_code if srv else None,
                service_name=srv.service_name if srv else None,
                applied_at=log.applied_at,
            )
            for log, srv in logs
        ]