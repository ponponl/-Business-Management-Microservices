from typing import List, Union
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.pricing import (
    PriceList,
    PriceListVersion,
    PriceListDetail,
    ServiceItem,
    PriceChangeHistory,
    PriceListUsageLog,
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
    def get_version_history_list(
        db: Session, 
        price_list_identifier: str  # Chấp nhận cả UUID lẫn Mã string như 'PL-2026-515'
    ) -> List[VersionHistoryItem]:
        """Lấy danh sách các phiên bản ở Cột bên trái (Sidebar)."""
        
        # 1. Tìm PriceList theo UUID hoặc Price List Code
        price_list_query = db.query(PriceList)
        
        # Kiểm tra nếu tham số truyền vào là chuỗi UUID chuẩn
        is_valid_uuid = False
        try:
            uuid_obj = UUID(price_list_identifier)
            is_valid_uuid = True
        except ValueError:
            is_valid_uuid = False

        if is_valid_uuid:
            price_list = price_list_query.filter(
                or_(PriceList.id == uuid_obj, PriceList.price_list_code == price_list_identifier)
            ).first()
        else:
            price_list = price_list_query.filter(
                PriceList.price_list_code == price_list_identifier
            ).first()

        if not price_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Không tìm thấy bảng giá với mã hoặc ID: {price_list_identifier}"
            )

        # 2. Query phiên bản bằng ID chuẩn vừa tìm được
        versions = (
            db.query(PriceListVersion)
            .filter(PriceListVersion.price_list_id == price_list.id)
            .order_by(PriceListVersion.created_at.desc())
            .all()
        )

        return [
            VersionHistoryItem(
                id=v.id,
                version_number=v.version_number,
                status=v.status,
                valid_from=v.valid_from,
                valid_to=v.valid_to,
            )
            for v in versions
        ]

    @staticmethod
    def get_version_details(db: Session, version_id: UUID) -> VersionDetailResponse:
        """Tab 1: Thông tin chung bảng giá & Cấu hình đơn giá chi tiết của phiên bản."""
        version = db.query(PriceListVersion).filter(PriceListVersion.id == version_id).first()
        if not version:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phiên bản không tồn tại.")

        price_list = db.query(PriceList).filter(PriceList.id == version.price_list_id).first()

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
                unit_price=float(dt.unit_price),
            )
            for dt, srv in details
        ]

        return VersionDetailResponse(
            price_list_id=price_list.id,
            price_list_code=price_list.price_list_code,
            price_list_name=price_list.price_list_name,
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
        """Tab 2: Nhật ký thay đổi của phiên bản."""
        logs = (
            db.query(PriceChangeHistory)
            .filter(PriceChangeHistory.price_list_version_id == version_id)
            .order_by(PriceChangeHistory.changed_at.desc())
            .all()
        )
        return [
            ChangeHistoryItem(
                id=log.id,
                entity_type=log.entity_type,
                entity_name=log.entity_name,
                field_name=log.field_name,
                old_value=log.old_value,
                new_value=log.new_value,
                change_reason=log.change_reason,
                changed_by=log.changed_by,
                changed_at=log.changed_at,
            )
            for log in logs
        ]

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
            for log in logs
        ]