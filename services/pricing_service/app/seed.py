import uuid
from datetime import date, datetime

from app.db.session import Base, SessionLocal, engine
import app.models.pricing 
from app.models.pricing import (
    PriceChangeHistory,
    PriceList,
    PriceListDetail,
    PriceListUsageLog,
    PriceListVersion,
    ServiceItem,
)


def seed_rich_data():
    print("1. Đang Drop và Re-create lại toàn bộ Bảng trong Database...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("2. Đang khởi tạo danh mục Dịch vụ (SERVICE_ITEM)...")
        # Định dạng: (code, name, service_group, unit)
        services_data = [
            ("SRV-20ft-IN", "Bốc xếp container 20ft (Hàng nhập)", "Bốc xếp & Nâng hạ", "Container"),
            ("SRV-WH-GEN", "Lưu kho bãi tổng hợp", "Lưu kho & Bãi container", "Ngày/Tấn"),
            ("SRV-PORT-OP", "Khai thác bến bãi hạ tải", "Dịch vụ Cảng & Bến bãi", "Lượt xe"),
            ("SRV-40ft-OUT", "Bốc xếp container 40ft (Hàng xuất)", "Bốc xếp & Nâng hạ", "Container"),
            ("SRV-CUST-CLR", "Khai báo hải quan trọn gói", "Thủ tục Hải quan", "Tờ khai"),
        ]

        service_objects = {}
        for code, name, s_group, unit in services_data:
            item = ServiceItem(
                id=uuid.uuid4(),
                service_code=code,
                service_name=name,
                service_group=s_group,
                unit=unit,
                status="ACTIVE",
            )
            db.add(item)
            service_objects[code] = item
        db.flush()

        print("3. Đang khởi tạo Bảng giá và các Phiên bản (kèm price_list_name)...")

        # Định danh User theo đúng Role
        staff_user_id = uuid.UUID("55399947-e92e-4afb-a8af-572b84050f4b")
        manager_user_id = uuid.UUID("31ef2ba5-15d4-4411-afa1-d1661dd6719f")
        director_user_id = uuid.UUID("030b4950-4ccf-4437-bf14-5c8debfa3e8d")

        detailed_rejection_reasons = [
            "Đơn giá dịch vụ lưu kho bãi vượt quá định mức chiết khấu cho phép 15% so với chính sách chung của công ty.",
            "Thiếu phụ lục hợp đồng cam kết sản lượng tối thiểu đi kèm đối với khách hàng VIP.",
            "Thời gian hiệu lực bảng giá trùng lặp với Bảng giá ưu đãi Q1/2026 đang áp dụng.",
            "Cơ cấu đơn giá bốc xếp container 40ft chưa cập nhật chi phí phụ trội nhiên liệu theo quy định mới.",
        ]

        price_lists_raw = [
            ("PL-2026-001", "Cảng Cát Lái", "CUSTOMER", "v3.0", "SUBMITTED", date(2026, 1, 1), date(2026, 12, 31)),
            ("PL-2026-002", "Công ty CP XNK Đại Dương", "CONTRACT", "v1.0", "DRAFT", date(2026, 6, 1), date(2027, 6, 30)),
            ("PL-2026-003", "Cảng Cái Mép Thượng", "GENERAL", "v2.0", "EFFECTIVE", date(2026, 6, 1), date(2026, 12, 31)),
            ("PL-2026-004", "Cty TNHH Vận tải Phương Nam", "CUSTOMER", "v1.0", "REJECTED", date(2026, 6, 1), date(2026, 12, 31)),
            ("PL-2026-005", "Cảng Cát Lái", "CUSTOMER", "v2.0", "EFFECTIVE", date(2026, 5, 1), date(2026, 11, 30)),
            ("PL-2026-006", "Tập đoàn Hòa Phát", "SERVICE_GROUP", "v1.0", "SUBMITTED", date(2026, 6, 15), date(2027, 6, 15)),
            ("PL-2026-007", "Kho vận Gemadept", "SERVICE_GROUP", "v4.0", "EFFECTIVE", date(2026, 1, 1), date(2026, 12, 31)),
            ("PL-2026-008", "Logistics TTC", "CUSTOMER", "v1.0", "DRAFT", date(2026, 7, 1), date(2026, 12, 31)),
            ("PL-2026-009", "Cảng Quốc Tế Tân Cảng", "CONTRACT", "v2.0", "SUBMITTED", date(2026, 6, 20), date(2027, 6, 20)),
            ("PL-2026-010", "Tổng kho Vĩnh Long", "GENERAL", "v1.0", "EFFECTIVE", date(2026, 1, 1), date(2026, 12, 31)),
            ("PL-2026-011", "Vận Tải Phương Hoàng", "CUSTOMER", "v1.0", "REJECTED", date(2026, 3, 1), date(2026, 12, 31)),
            ("PL-2026-012", "Bảng giá bốc xếp hạ tải nội địa 2026", "CUSTOMER", "v1.0", "DRAFT", date(2026, 7, 20), date(2027, 7, 20)),
            ("PL-2026-013", "Kho lạnh Tân Tạo - Khách mới", "CUSTOMER", "v1.0", "DRAFT", date(2026, 8, 1), date(2026, 12, 31)),
            ("PL-2026-014", "Dịch vụ Hải quan Tân Cảng Quý 3", "SERVICE_GROUP", "v1.0", "DRAFT", date(2026, 9, 1), date(2026, 12, 31)),
            ("PL-2026-015", "Hợp đồng nguyên tắc Vinalines", "CONTRACT", "v1.0", "DRAFT", date(2026, 8, 15), date(2027, 8, 15)),
            ("PL-2026-016", "Cảng Phước Long - Khách VIP", "CUSTOMER", "v1.0", "APPROVED", date(2026, 10, 1), date(2027, 10, 1)),
            ("PL-2026-017", "Bảng giá dịch vụ lưu kho Q4/2026", "SERVICE_GROUP", "v2.0", "APPROVED", date(2026, 11, 1), date(2027, 5, 31)),
            ("PL-2026-018", "Hợp đồng Vận chuyển Hàng không DHL", "CONTRACT", "v1.0", "APPROVED", date(2026, 12, 1), date(2027, 12, 31)),
            ("PL-2025-089", "Cảng Cát Lái - Bảng giá cũ 2025", "CUSTOMER", "v1.0", "SUPERSEDED", date(2025, 1, 1), date(2025, 12, 31)),
            ("PL-2025-090", "Tập đoàn Hòa Phát - Hợp đồng cũ", "SERVICE_GROUP", "v1.0", "SUPERSEDED", date(2025, 6, 1), date(2026, 5, 31)),
            ("PL-2024-012", "Kho vận Gemadept - Niêm yết 2024", "SERVICE_GROUP", "v3.0", "EXPIRED", date(2024, 1, 1), date(2024, 12, 31)),
            ("PL-2025-045", "Dịch vụ Hải quan Tân Cảng 2025", "SERVICE_GROUP", "v1.0", "EXPIRED", date(2025, 1, 1), date(2025, 12, 31)),
        ]

        for idx, (code, name, scope_type, ver_num, status, valid_from, valid_to) in enumerate(price_lists_raw):
            # Tạo Bảng giá gốc (PriceList)
            pl = PriceList(
                id=uuid.uuid4(),
                price_list_code=code,
                price_list_name=name,
                scope_type=scope_type,
                scope_id="SCOPE-" + code,
                description=f"Cấu hình bảng giá cho {name}",
                created_by=staff_user_id,
                is_deleted=False,
            )
            db.add(pl)
            db.flush()

            rejection_note = None
            approver_id = None

            if status in ["EFFECTIVE", "SUPERSEDED", "EXPIRED"]:
                stage = "COMPLETED"
                approver_id = director_user_id
            elif status == "APPROVED":
                stage = "APPROVED"
                approver_id = director_user_id
            elif status == "REJECTED":
                stage = "REJECTED"
                approver_id = manager_user_id
                rejection_note = detailed_rejection_reasons[idx % len(detailed_rejection_reasons)]
            elif status == "SUBMITTED":
                stage = "MANAGER_PENDING"
            else:
                stage = "DRAFT"

            # Tạo Phiên bản Bảng giá (PriceListVersion) - Thêm gán price_list_name
            ver = PriceListVersion(
                id=uuid.uuid4(),
                price_list_id=pl.id,
                price_list_name=name,  # Bổ sung gán tên bảng giá cho từng phiên bản
                version_number=ver_num,
                valid_from=valid_from,
                valid_to=valid_to,
                status=status,
                created_by=staff_user_id,
                approved_by=approver_id,
                rejected_reason=rejection_note,
                approval_stage=stage,
            )
            db.add(ver)
            db.flush()

            prices = {
                "SRV-20ft-IN": 350000.00,
                "SRV-WH-GEN": 42000.00 if ver_num == "v3.0" else 45000.00,
                "SRV-PORT-OP": 125000.00 if ver_num == "v3.0" else 120000.00,
                "SRV-40ft-OUT": 550000.00,
                "SRV-CUST-CLR": 800000.00,
            }

            for srv_code, price_val in prices.items():
                detail = PriceListDetail(
                    id=uuid.uuid4(),
                    price_list_id=pl.id,
                    price_list_version_id=ver.id,
                    service_item_id=service_objects[srv_code].id,
                    unit_price=price_val,
                )
                db.add(detail)

            if code == "PL-2026-001":
                history_1 = PriceChangeHistory(
                    id=uuid.uuid4(),
                    price_list_version_id=ver.id,
                    entity_type="PRICE_LIST",
                    entity_name=name,
                    field_name="price_list_name",
                    old_value="Bảng giá bốc xếp 2026",
                    new_value="Bảng giá bốc hạ tải nội địa 2027",
                    change_reason="Điều chỉnh tên gọi chuẩn theo danh mục bảng giá niêm yết mới",
                    changed_by=staff_user_id,
                    changed_at=datetime(2026, 7, 20, 9, 12),
                )
                db.add(history_1)

                for _ in range(4):
                    log = PriceListUsageLog(
                        id=uuid.uuid4(),
                        price_list_version_id=ver.id,
                        payment_board_id=uuid.uuid4(),
                        service_item_id=service_objects["SRV-20ft-IN"].id,
                        applied_at=datetime.utcnow(),
                    )
                    db.add(log)

        db.commit()
        print("Tạo thành công dữ liệu mẫu với đầy đủ price_list_name cho từng Phiên bản!")

    except Exception as e:
        db.rollback()
        print(f"Lỗi khi seed dữ liệu: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_rich_data()