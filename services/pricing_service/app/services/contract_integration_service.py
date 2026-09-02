from datetime import date
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.pricing import PriceList, PriceListDetail, PriceListVersion, ServiceItem
from app.schemas.contract_integration import (
    ContractServiceItemResponse,
    ContractServicesResponse,
)


class ContractIntegrationService:

    @staticmethod
    def get_services_by_contract(db: Session, contract_id: str) -> ContractServicesResponse:
        """
        Lấy danh sách dịch vụ và đơn giá áp dụng cho một contract_id.
        Ưu tiên bản record có status EFFECTIVE / APPROVED và còn hiệu lực ngày.
        """
        today = date.today()

        # 1. Tìm PriceList có scope_id trùng với contract_id
        price_list = db.query(PriceList).filter(
            PriceList.scope_id == contract_id,
            PriceList.is_deleted == False
        ).first()

        if not price_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy Bảng giá cho Hợp đồng '{contract_id}'."
            )

        # 2. Lấy phiên bản đang có hiệu lực (EFFECTIVE/APPROVED)
        active_version = db.query(PriceListVersion).filter(
            PriceListVersion.price_list_id == price_list.id,
            PriceListVersion.status.in_(["EFFECTIVE", "APPROVED"]),
            PriceListVersion.valid_from <= today,
            (PriceListVersion.valid_to.is_(None) | (PriceListVersion.valid_to >= today))
        ).order_by(PriceListVersion.created_at.desc()).first()

        # Fallback lấy phiên bản mới nhất nếu không có bản active chuẩn
        if not active_version:
            active_version = db.query(PriceListVersion).filter(
                PriceListVersion.price_list_id == price_list.id
            ).order_by(PriceListVersion.created_at.desc()).first()

        if not active_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy phiên bản bảng giá khả dụng cho Hợp đồng '{contract_id}'."
            )

        # 3. Query chi tiết các Dịch vụ trong phiên bản Bảng giá
        details = db.query(PriceListDetail, ServiceItem).join(
            ServiceItem, PriceListDetail.service_item_id == ServiceItem.id
        ).filter(
            PriceListDetail.price_list_version_id == active_version.id
        ).all()

        services_list = []
        for detail, item in details:
            services_list.append(
                ContractServiceItemResponse(
                    service_item_id=item.id,
                    service_code=item.service_code,
                    service_name=item.service_name,
                    service_group=item.service_group,
                    unit=item.unit,
                    unit_price=detail.unit_price
                )
            )

        return ContractServicesResponse(
            contract_id=contract_id,
            price_list_id=price_list.id,
            price_list_code=price_list.price_list_code,
            price_list_name=price_list.price_list_name,
            version_id=active_version.id,
            version_number=active_version.version_number,
            services=services_list
        )